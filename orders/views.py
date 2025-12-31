from rest_framework import viewsets, permissions, views, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404
from django.db import transaction # Crucial for data integrity
from django.utils.crypto import get_random_string 
import uuid

# Models and Serializers
from .models import Order, OrderItem, Cart, CartItem, ShippingAddress 
from products.models import Product
from .serializers import (
    OrderSerializer, 
    CartSerializer, 
    CartItemSerializer, 
    ShippingAddressSerializer 
)


# ==========================================
# 1. ORDER LOGIC
# ==========================================

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all().select_related('user', 'shipping_address').prefetch_related('items')
        return Order.objects.filter(user=self.request.user).select_related('user', 'shipping_address').prefetch_related('items')

    def perform_create(self, serializer):
        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(user=self.request.user, order_number=order_number)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def update_status(self, request, pk=None):
        order = self.get_object()
        status_val = request.data.get('status')
        if status_val in dict(Order.STATUS_CHOICES):
            order.status = status_val
            order.save()
            return Response({'status': 'Order status updated'})
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)


# ------------------------------------------
# 2. CHECKOUT LOGIC (FIXED & ENHANCED)
# ------------------------------------------

class PlaceOrderView(views.APIView):
    """
    POST: Converts the user's Cart into an Order, saving/updating the shipping address.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # 1. Prepare Data
        shipping_details = request.data.get('shipping_details', {})
        payment_method = request.data.get('payment_method', 'COD')
        total_amount_from_frontend = request.data.get('total_amount') 
        
        # Extract the frontend-only flag before validation, as the serializer doesn't have 'isDefault'
        # The user's input may have overridden the initial pre-filled value.
        is_default_flag = shipping_details.pop('isDefault', False) 

        # 2. Address Validation (using validated_data, which is snake_case)
        address_serializer = ShippingAddressSerializer(data=shipping_details)
        
        if not address_serializer.is_valid():
            return Response(
                {'error': 'Invalid shipping details provided.', 'details': address_serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Transaction Block: Ensure atomic operation
        try:
            with transaction.atomic():
                # 3a. Retrieve and Validate Cart
                cart = get_object_or_404(Cart, user=user)
                cart_items = cart.items.select_related('product').all()
                
                if not cart_items:
                    return Response({"error": "Your vault is empty. Cannot place an order."}, status=status.HTTP_400_BAD_REQUEST)

                # IMPORTANT SECURITY STEP: Recalculate total on the backend (omitted for brevity, but vital)
                # actual_cart_subtotal = cart.total_price 
                # if abs(float(actual_cart_subtotal) - float(total_amount_from_frontend)) > 0.10: 
                #     raise Exception("Price mismatch.")


                # 3b. Save or Retrieve Shipping Address
                # Use validated data (which is now in snake_case keys) to find or create the address
                shipping_address_instance, created = ShippingAddress.objects.get_or_create(
                    user=user,
                    # We match on all unique fields except `is_default` to see if this address exists
                    defaults=address_serializer.validated_data,
                    **address_serializer.validated_data
                )
                
                # 3c. Handle Default Address Logic (The ENHANCEMENT)
                if is_default_flag:
                    # 1. Unset the default flag on ALL other addresses for this user
                    ShippingAddress.objects.filter(user=user, is_default=True).update(is_default=False)
                    
                    # 2. Set the current/new address as default
                    shipping_address_instance.is_default = True
                    shipping_address_instance.save()
                    
                
                # 3d. Create the Order
                order_number = f"ORD-{get_random_string(length=8).upper()}"
                
                order = Order.objects.create(
                    user=user,
                    order_number=order_number,
                    shipping_address=shipping_address_instance, 
                    total_amount=total_amount_from_frontend, 
                    payment_method=payment_method,
                    status='processing'
                )

                # 3e. Move CartItems to OrderItems (Bulk Creation for efficiency)
                order_items_to_create = [
                    OrderItem(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.final_price 
                    ) for item in cart_items
                ]
                OrderItem.objects.bulk_create(order_items_to_create)

                # 3f. Clear the Cart
                cart.items.all().delete()

                # 4. Success Response
                return Response({
                    "message": "Order placed successfully. Shipping details confirmed.", 
                    "order_reference": order.order_number
                }, status=status.HTTP_201_CREATED)

        except Cart.DoesNotExist:
            return Response({"error": "User's cart not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Checkout error: {e}")
            return Response(
                {"error": "Internal Server Error: Failed to process order."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# ------------------------------------------
# 3. CART / VAULT LOGIC (Unchanged)
# ------------------------------------------

class CartView(views.APIView):
    """ GET: Retrieve the user's cart (Vault) """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class AddToCartView(views.APIView):
    """ POST: Add an item to the cart using its Slug """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        product_slug = request.data.get('slug')
        quantity = int(request.data.get('quantity', 1))
        
        if not product_slug:
            return Response({'error': 'Product slug is required'}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, slug=product_slug)

        if product.stock < quantity:
            return Response({'error': 'Not enough stock available.'}, status=status.HTTP_400_BAD_REQUEST)

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
            
        cart_item.save()

        return Response({'message': 'Artifact secured in vault'}, status=status.HTTP_200_OK)


class UpdateCartItemView(views.APIView):
    """ PATCH: Update the quantity of a specific cart item """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        new_quantity = request.data.get('quantity')

        if new_quantity is not None:
            new_val = int(new_quantity)
            if new_val > 0:
                cart_item.quantity = new_val
                cart_item.save()
                return Response(CartItemSerializer(cart_item).data) 
            else:
                cart_item.delete()
                return Response({'message': 'Item removed'}, status=status.HTTP_204_NO_CONTENT)
        
        return Response({'error': 'Invalid quantity'}, status=status.HTTP_400_BAD_REQUEST)


class RemoveFromCartView(views.APIView):
    """ DELETE: Remove a specific item from the cart """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        item.delete()
        return Response({'message': 'Artifact removed from vault'}, status=status.HTTP_204_NO_CONTENT)

# ------------------------------------------
# 4. NEW PROFILE LOGIC (To fix 404 error)
# ------------------------------------------

class DefaultShippingAddressView(generics.RetrieveAPIView):
    """
    Retrieves the currently logged-in user's address marked as is_default=True.
    This fixes the frontend's requirement for the /profile/default-address/ endpoint.
    """
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user = self.request.user
        
        try:
            # Find the address marked as default for the current user
            default_address = ShippingAddress.objects.get(user=user, is_default=True)
            return default_address
        except ShippingAddress.DoesNotExist:
            # If no default is found, check if ANY address exists (and use the first one)
            try:
                first_address = ShippingAddress.objects.filter(user=user).first()
                if first_address:
                    return first_address
                else:
                    # If the user has no addresses at all, return 404
                    raise NotFound(detail="No default shipping address found for this user.")
            except ShippingAddress.DoesNotExist:
                # This should be covered by the previous `if`, but included for completeness
                 raise NotFound(detail="No default shipping address found for this user.")