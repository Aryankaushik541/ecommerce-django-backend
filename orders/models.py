from django.db import models
from django.contrib.auth.models import User
from django.conf import settings 
# Assuming 'Product' model is correctly imported from your products app
from products.models import Product 

# ==========================================
# 0. SHIPPING ADDRESS MODEL
# ==========================================

class ShippingAddress(models.Model):
    """Stores a detailed, reusable shipping address."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='shipping_addresses', 
        null=True, 
        blank=True
    )
    
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    is_default = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.full_name} - {self.address}, {self.city}'


# ==========================================
# 1. UPDATED ORDER MODELS
# ==========================================

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    shipping_address = models.ForeignKey(
        ShippingAddress, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True
    ) 
    
    payment_method = models.CharField(max_length=50, default='COD')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def subtotal(self):
        # FIX IMPLEMENTED: Safely handle NoneType in case self.price is NULL/None
        item_price = self.price if self.price is not None else 0
        return self.quantity * item_price


# ==========================================
# 2. CART MODELS (The Vault)
# ==========================================

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Vault of {self.user.username}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        # Assumes Product model has a 'final_price' property/field
        return self.product.final_price * self.quantity

    @property
    def image_url(self):
        try:
            if self.product.image:
                return self.product.image.url
        except AttributeError:
            return None 
        return None