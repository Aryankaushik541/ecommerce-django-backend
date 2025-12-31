from django.contrib import admin
from django.utils.safestring import mark_safe # REQUIRED for rendering HTML
from .models import Order, OrderItem, Cart, CartItem, ShippingAddress 

# ------------------------------------------
# 0. SHIPPING ADDRESS ADMINISTRATION
# ------------------------------------------

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    """Admin interface for managing reusable shipping addresses."""
    list_display = ['full_name', 'user', 'city', 'zip_code', 'is_default']
    list_filter = ['is_default', 'state', 'city']
    search_fields = ['full_name', 'phone', 'address', 'city', 'user__username']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'full_name', 'phone', 'is_default')
        }),
        ('Location Details', {
            'fields': ('address', 'city', 'state', 'zip_code')
        }),
    )

# ------------------------------------------
# 1. ORDER ADMINISTRATION (FINAL)
# ------------------------------------------

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    
    # Wrapper method to correctly display the @property 'subtotal'
    def line_item_subtotal(self, obj):
        return obj.subtotal
    line_item_subtotal.short_description = 'Line Subtotal'

    readonly_fields = ['line_item_subtotal'] 

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # Uses a new concise method for list view (optional but good practice)
    list_display = ['order_number', 'user', 'shipping_address_for_list', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'payment_method']
    
    search_fields = [
        'order_number', 
        'user__username', 
        'shipping_address__full_name',
        'shipping_address__phone'
    ]
    
    inlines = [OrderItemInline]
    
    # The detail view uses 'shipping_detail_display'
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'shipping_detail_display'] 
    
    # METHOD FOR DETAIL VIEW (The main fix)
    def shipping_detail_display(self, obj):
        if obj.shipping_address:
            address = obj.shipping_address
            # Using mark_safe to render HTML for clean formatting
            html = f"""
            <strong>Recipient:</strong> {address.full_name}<br/>
            <strong>Phone:</strong> {address.phone}<br/>
            <strong>Address:</strong> {address.address}<br/>
            {address.city}, {address.state} - {address.zip_code}
            """
            return mark_safe(html)
        return "No Shipping Address Attached"
    
    shipping_detail_display.short_description = 'Shipping Address Details'
    
    # METHOD FOR LIST VIEW (Concise details for the table overview)
    def shipping_address_for_list(self, obj):
        if obj.shipping_address:
            address = obj.shipping_address
            html = f"""
            {address.full_name}<br/>
            <small style="color:#aaa;">{address.city}, {address.zip_code}</small>
            """
            return mark_safe(html)
        return "N/A"
    shipping_address_for_list.short_description = 'Ship To Details'

    
    # FIELDSETS: Uses the custom display method
    fieldsets = (
        (None, {
            'fields': ('user', 'order_number', 'status', 'payment_method', 'total_amount', 'notes')
        }),
        ('Shipping & Timeline', {
            # This is the line that now displays the full formatted address:
            'fields': ('shipping_detail_display', 'created_at', 'updated_at'),
            'description': 'The permanent shipping details used for this acquisition.'
        }),
    )

# ------------------------------------------
# 2. CART / VAULT ADMINISTRATION
# ------------------------------------------

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['total_price'] 

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_price', 'updated_at']
    search_fields = ['user__username', 'user__email']
    inlines = [CartItemInline]
    
    readonly_fields = ['total_price']