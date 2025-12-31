# orders/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet, 
    CartView, 
    AddToCartView, 
    UpdateCartItemView, 
    RemoveFromCartView,
    PlaceOrderView,
    DefaultShippingAddressView 
)

router = DefaultRouter()
# NOTE: register with empty prefix instead of 'orders'
router.register(r'', OrderViewSet, basename='order')

urlpatterns = [
    # Cart / Vault endpoints
    path('cart/', CartView.as_view(), name='cart-detail'),
    path('cart/add/', AddToCartView.as_view(), name='cart-add'),
    path('cart/update/<int:pk>/', UpdateCartItemView.as_view(), name='cart-update'),
    path('cart/remove/<int:pk>/', RemoveFromCartView.as_view(), name='cart-remove'),

    # Checkout
    path('place-order/', PlaceOrderView.as_view(), name='place-order'),

    # Default address
    path('profile/default-address/', DefaultShippingAddressView.as_view(), name='default-address'),

    # Order endpoints (now mounted at /api/orders/)
    path('', include(router.urls)),
]
