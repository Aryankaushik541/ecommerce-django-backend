from django.urls import path
from . import views

urlpatterns = [
    # Home and products
    path('', views.home, name='home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('payment-selection/<int:pk>/', views.payment_selection, name='payment_selection'),
    
    # Stripe
    path('stripe/payment/<int:pk>/', views.stripe_payment, name='stripe_payment'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    
    # Razorpay
    path('razorpay/payment/<int:pk>/', views.razorpay_payment, name='razorpay_payment'),
    path('razorpay/verify/', views.razorpay_verify, name='razorpay_verify'),
    
    # Success/Failure
    path('success/', views.payment_success, name='payment_success'),
    path('failed/', views.payment_failed, name='payment_failed'),
    
    # Payment history
    path('history/', views.payment_history, name='payment_history'),
    path('payment/<int:pk>/', views.payment_detail, name='payment_detail'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
]