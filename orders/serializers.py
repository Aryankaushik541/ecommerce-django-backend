from rest_framework import serializers
from .models import Order, OrderItem, Cart, CartItem, ShippingAddress # Import ShippingAddress
from products.models import Product
from products.serializers import ProductSerializer


# ==========================================
# 0. NEW ADDRESS SERIALIZER (for Validation)
# ==========================================

class ShippingAddressSerializer(serializers.ModelSerializer):
    """
    Handles validation for shipping details received from the frontend.
    Maps frontend camelCase keys (e.g., fullName) to backend snake_case keys (full_name).
    """
    # Custom fields to map frontend names to backend model fields
    fullName = serializers.CharField(source='full_name')
    zipCode = serializers.CharField(source='zip_code')

    class Meta:
        model = ShippingAddress
        # Note: 'state' and 'address' are included implicitly via model fields
        fields = ['id', 'fullName', 'phone', 'address', 'city', 'state', 'zipCode']
        read_only_fields = ['id']

    def validate(self, data):
        """Custom validation for postal/zip code."""
        # The data dict here uses the backend field names ('full_name', 'zip_code')
        zip_code = data.get('zip_code')
        if zip_code and (not zip_code.isdigit() or len(zip_code) < 5):
            raise serializers.ValidationError({"zipCode": "Invalid postal code format. Must be at least 5 digits."})
        return data


# ----------------------------------------------------

# ==========================================
# 1. EXISTING ORDER SERIALIZERS (MODIFIED)
# ==========================================

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_image', 'quantity', 'price', 'subtotal']

    def get_product_image(self, obj):
        try:
            # Assumes your Product model has an 'image' field
            return obj.product.image.url if obj.product.image else None
        except AttributeError:
            return None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    # MODIFIED: Nest the ShippingAddressSerializer for reading
    shipping_address = ShippingAddressSerializer(read_only=True)
    
    # NEW: Include payment method
    payment_method = serializers.CharField(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'user', 'user_email', 'total_amount', 
                  'status', 'shipping_address', 'payment_method', 'notes', 
                  'items', 'created_at', 'updated_at']
        read_only_fields = ['order_number', 'user']

# ----------------------------------------------------

# ==========================================
# 2. CART SERIALIZERS (No changes needed)
# ==========================================

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    image_url = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'total_price', 'image_url']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price']