from rest_framework import serializers
from .models import Order, OrderItem
from products.serializers import ProductSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'user', 'user_email', 'total_amount', 
                  'status', 'shipping_address', 'phone', 'email', 'notes', 
                  'items', 'created_at', 'updated_at']
        read_only_fields = ['order_number', 'user']
