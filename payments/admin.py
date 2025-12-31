from django.contrib import admin
from .models import Payment, Transaction, PaymentLog

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'order', 'amount', 'currency', 'provider', 'status', 'created_at']
    list_filter = ['provider', 'status', 'currency', 'created_at']
    search_fields = ['payment_id', 'order_id', 'customer_email', 'customer_name']
    readonly_fields = ['payment_id', 'created_at', 'updated_at', 'completed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('payment_id', 'order_id', 'order', 'user')
        }),
        ('Amount Details', {
            'fields': ('amount', 'currency', 'provider', 'status')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone')
        }),
        ('Additional Data', {
            'fields': ('metadata', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'payment', 'transaction_type', 'amount', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['transaction_id', 'payment__payment_id']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'payment', 'level', 'message', 'created_at']
    list_filter = ['level', 'event_type', 'created_at']
    search_fields = ['event_type', 'message', 'payment__payment_id']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'