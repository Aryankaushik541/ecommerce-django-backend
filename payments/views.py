from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Product, Payment, Transaction, PaymentLog
import stripe
import razorpay
import json
import uuid
import logging

logger = logging.getLogger(__name__)

# Initialize payment clients
stripe.api_key = settings.STRIPE_SECRET_KEY
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def log_payment_event(payment, event_type, message, data=None, level='info'):
    """Helper function to log payment events"""
    PaymentLog.objects.create(
        payment=payment,
        event_type=event_type,
        message=message,
        data=data or {},
        level=level
    )


# ==================== HOME & PRODUCT VIEWS ====================

def home(request):
    """Display all active products"""
    products = Product.objects.filter(is_active=True)
    context = {
        'products': products,
        'total_products': products.count(),
    }
    return render(request, 'payments/home.html', context)


def product_detail(request, pk):
    """Display product details"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    context = {
        'product': product,
    }
    return render(request, 'payments/product_detail.html', context)


def payment_selection(request, pk):
    """Payment method selection page"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    context = {
        'product': product,
        'stripe_enabled': bool(settings.STRIPE_PUBLIC_KEY),
        'razorpay_enabled': bool(settings.RAZORPAY_KEY_ID),
    }
    return render(request, 'payments/payment_selection.html', context)


# ==================== STRIPE PAYMENT ====================

def stripe_payment(request, pk):
    """Stripe payment form"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    
    if request.method == 'POST':
        try:
            # Get customer details
            customer_name = request.POST.get('name', '').strip()
            customer_email = request.POST.get('email', '').strip()
            
            if not customer_name or not customer_email:
                messages.error(request, 'Please provide both name and email')
                return redirect('stripe_payment', pk=pk)
            
            # Create Stripe Payment Intent
            amount = int(product.price * 100)  # Convert to cents
            
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=product.currency.lower(),
                metadata={
                    'product_id': product.id,
                    'product_name': product.name,
                    'customer_name': customer_name,
                    'customer_email': customer_email,
                },
                description=f"Payment for {product.name}",
            )
            
            # Create payment record
            payment = Payment.objects.create(
                product=product,
                payment_id=intent.id,
                amount=product.price,
                currency=product.currency,
                provider='stripe',
                status='pending',
                customer_email=customer_email,
                customer_name=customer_name,
                metadata={
                    'intent_id': intent.id,
                    'client_secret': intent.client_secret,
                }
            )
            
            # Log event
            log_payment_event(
                payment=payment,
                event_type='payment_intent_created',
                message=f'Stripe payment intent created for {product.name}',
                data={'intent_id': intent.id, 'amount': amount}
            )
            
            context = {
                'product': product,
                'client_secret': intent.client_secret,
                'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
                'payment': payment,
                'customer_name': customer_name,
                'customer_email': customer_email,
            }
            
            return render(request, 'payments/stripe_checkout.html', context)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {str(e)}")
            messages.error(request, f'Payment error: {str(e)}')
            return redirect('product_detail', pk=pk)
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            messages.error(request, f'Error: {str(e)}')
            return redirect('product_detail', pk=pk)
    
    context = {
        'product': product,
    }
    return render(request, 'payments/stripe_payment.html', context)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)
    
    # Handle different event types
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        try:
            payment = Payment.objects.get(payment_id=payment_intent['id'])
            payment.status = 'succeeded'
            payment.completed_at = timezone.now()
            payment.save()
            
            # Create transaction record
            Transaction.objects.create(
                payment=payment,
                transaction_id=payment_intent.get('id'),
                transaction_type='charge',
                amount=payment.amount,
                status='succeeded',
                raw_response=payment_intent
            )
            
            log_payment_event(
                payment=payment,
                event_type='payment_succeeded',
                message='Payment completed successfully',
                data=payment_intent
            )
            
        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for intent: {payment_intent['id']}")
    
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        
        try:
            payment = Payment.objects.get(payment_id=payment_intent['id'])
            payment.status = 'failed'
            payment.save()
            
            log_payment_event(
                payment=payment,
                event_type='payment_failed',
                message='Payment failed',
                data=payment_intent,
                level='error'
            )
            
        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for intent: {payment_intent['id']}")
    
    return HttpResponse(status=200)


# ==================== RAZORPAY PAYMENT ====================

def razorpay_payment(request, pk):
    """Razorpay payment form"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    
    if request.method == 'POST':
        try:
            # Get customer details
            customer_name = request.POST.get('name', '').strip()
            customer_email = request.POST.get('email', '').strip()
            customer_phone = request.POST.get('phone', '').strip()
            
            if not customer_name or not customer_email:
                messages.error(request, 'Please provide both name and email')
                return redirect('razorpay_payment', pk=pk)
            
            # Create Razorpay Order
            amount = int(product.price * 100)  # Convert to paise
            
            order_data = {
                'amount': amount,
                'currency': 'INR',
                'payment_capture': 1,
                'notes': {
                    'product_id': str(product.id),
                    'product_name': product.name,
                    'customer_name': customer_name,
                    'customer_email': customer_email,
                }
            }
            
            order = razorpay_client.order.create(data=order_data)
            
            # Create payment record
            payment = Payment.objects.create(
                product=product,
                payment_id=str(uuid.uuid4()),  # Temporary ID, will be updated on verification
                order_id=order['id'],
                amount=product.price,
                currency='INR',
                provider='razorpay',
                status='pending',
                customer_email=customer_email,
                customer_name=customer_name,
                customer_phone=customer_phone,
                metadata={
                    'order_id': order['id'],
                }
            )
            
            log_payment_event(
                payment=payment,
                event_type='order_created',
                message=f'Razorpay order created for {product.name}',
                data={'order_id': order['id'], 'amount': amount}
            )
            
            context = {
                'product': product,
                'order_id': order['id'],
                'amount': amount,
                'currency': 'INR',
                'razorpay_key': settings.RAZORPAY_KEY_ID,
                'payment': payment,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
            }
            
            return render(request, 'payments/razorpay_checkout.html', context)
            
        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay error: {str(e)}")
            messages.error(request, f'Payment error: {str(e)}')
            return redirect('product_detail', pk=pk)
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            messages.error(request, f'Error: {str(e)}')
            return redirect('product_detail', pk=pk)
    
    context = {
        'product': product,
    }
    return render(request, 'payments/razorpay_payment.html', context)


@csrf_exempt
@require_POST
def razorpay_verify(request):
    """Verify Razorpay payment"""
    try:
        data = json.loads(request.body)
        
        # Verify payment signature
        params_dict = {
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        }
        
        # This will raise an exception if signature is invalid
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        # Update payment record
        payment = Payment.objects.get(order_id=data['razorpay_order_id'])
        payment.payment_id = data['razorpay_payment_id']
        payment.status = 'succeeded'
        payment.completed_at = timezone.now()
        payment.save()
        
        # Create transaction record
        Transaction.objects.create(
            payment=payment,
            transaction_id=data['razorpay_payment_id'],
            transaction_type='charge',
            amount=payment.amount,
            status='succeeded',
            raw_response=data
        )
        
        log_payment_event(
            payment=payment,
            event_type='payment_verified',
            message='Razorpay payment verified successfully',
            data=data
        )
        
        return JsonResponse({
            'status': 'success',
            'payment_id': payment.payment_id
        })
        
    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"Signature verification failed: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Payment verification failed'
        }, status=400)
    except Payment.DoesNotExist:
        logger.error(f"Payment not found for order: {data.get('razorpay_order_id')}")
        return JsonResponse({
            'status': 'error',
            'message': 'Payment record not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


# ==================== SUCCESS & FAILURE PAGES ====================

def payment_success(request):
    """Payment success page"""
    payment_id = request.GET.get('payment_id')
    payment = None
    
    if payment_id:
        try:
            payment = Payment.objects.select_related('product').get(payment_id=payment_id)
        except Payment.DoesNotExist:
            messages.warning(request, 'Payment record not found')
    
    context = {
        'payment': payment,
    }
    return render(request, 'payments/success.html', context)


def payment_failed(request):
    """Payment failure page"""
    return render(request, 'payments/failed.html')


# ==================== PAYMENT HISTORY ====================

def payment_history(request):
    """Display all payments"""
    payments = Payment.objects.select_related('product').all()
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        payments = payments.filter(status=status_filter)
    
    # Filter by provider if provided
    provider_filter = request.GET.get('provider')
    if provider_filter:
        payments = payments.filter(provider=provider_filter)
    
    context = {
        'payments': payments,
        'status_filter': status_filter,
        'provider_filter': provider_filter,
        'status_choices': Payment.STATUS_CHOICES,
        'provider_choices': Payment.PROVIDER_CHOICES,
    }
    return render(request, 'payments/payment_history.html', context)


def payment_detail(request, pk):
    """Display payment details"""
    payment = get_object_or_404(
        Payment.objects.select_related('product'),
        pk=pk
    )
    transactions = payment.transactions.all()
    logs = payment.logs.all()[:20]  # Last 20 logs
    
    context = {
        'payment': payment,
        'transactions': transactions,
        'logs': logs,
    }
    return render(request, 'payments/payment_detail.html', context)


# ==================== DASHBOARD ====================

def dashboard(request):
    """Admin dashboard with payment statistics"""
    from django.db.models import Sum, Count, Q
    from datetime import timedelta
    
    # Get statistics
    total_payments = Payment.objects.count()
    successful_payments = Payment.objects.filter(status='succeeded').count()
    failed_payments = Payment.objects.filter(status='failed').count()
    pending_payments = Payment.objects.filter(status='pending').count()
    
    # Revenue statistics
    total_revenue = Payment.objects.filter(
        status='succeeded'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Recent payments
    recent_payments = Payment.objects.select_related('product').order_by('-created_at')[:10]
    
    # Provider statistics
    stripe_count = Payment.objects.filter(provider='stripe').count()
    razorpay_count = Payment.objects.filter(provider='razorpay').count()
    
    context = {
        'total_payments': total_payments,
        'successful_payments': successful_payments,
        'failed_payments': failed_payments,
        'pending_payments': pending_payments,
        'total_revenue': total_revenue,
        'recent_payments': recent_payments,
        'stripe_count': stripe_count,
        'razorpay_count': razorpay_count,
    }
    return render(request, 'payments/dashboard.html', context)