from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    """Product model for items available for purchase"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD', 
                                choices=[('USD', 'USD'), ('INR', 'INR')])
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'


class Payment(models.Model):
    """Payment model to track all payment transactions"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    PROVIDER_CHOICES = [
        ('stripe', 'Stripe'),
        ('razorpay', 'Razorpay'),
    ]
    
    # Relationships
    user = models.ForeignKey(User, on_delete=models.SET_NULL, 
                            null=True, blank=True, related_name='payments')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='payments')
    
    # Payment identifiers
    payment_id = models.CharField(max_length=200, unique=True, db_index=True)
    order_id = models.CharField(max_length=200, blank=True, null=True)
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Provider and status
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, 
                             default='pending', db_index=True)
    
    # Customer information
    customer_email = models.EmailField(blank=True, null=True)
    customer_name = models.CharField(max_length=200, blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Additional data
    metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.provider.upper()} - {self.payment_id} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['provider']),
        ]


class Transaction(models.Model):
    """Transaction model to track individual payment events"""
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, 
                               related_name='transactions')
    
    # Transaction details
    transaction_id = models.CharField(max_length=200, blank=True, null=True)
    transaction_type = models.CharField(max_length=50)  # charge, refund, capture, etc.
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)
    
    # Raw data from payment provider
    raw_response = models.JSONField(default=dict)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'


class PaymentLog(models.Model):
    """Log model for debugging and tracking payment events"""
    
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, 
                               related_name='logs', null=True, blank=True)
    
    event_type = models.CharField(max_length=100)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    level = models.CharField(max_length=20, default='info',
                            choices=[
                                ('debug', 'Debug'),
                                ('info', 'Info'),
                                ('warning', 'Warning'),
                                ('error', 'Error'),
                            ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.event_type} - {self.level} - {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Log'
        verbose_name_plural = 'Payment Logs'