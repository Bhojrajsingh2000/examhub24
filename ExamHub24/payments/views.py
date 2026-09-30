from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from subscriptions.models import Coupon, Plan, UserSubscription

from .models import AffiliatePartner, Order, Transaction

try:
    import razorpay
except ImportError:
    razorpay = None

AFFILIATE_SESSION_KEY = 'affiliate_code'


def _razorpay_client():
    if razorpay and settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    return None


def affiliate_link(request, code):
    """
    A partner's shareable referral link (e.g. examhub24.com/go/JOHN10/) — stores the code
    in the session so it can be credited on whatever plan the visitor eventually buys,
    then sends them on to the plans page. Silently ignores unknown/inactive codes rather
    than erroring, since a broken referral link shouldn't block someone from browsing.
    """
    if AffiliatePartner.objects.filter(code=code.upper(), is_active=True).exists():
        request.session[AFFILIATE_SESSION_KEY] = code.upper()
    return redirect('subscriptions:plans')


@login_required
def create_order(request, plan_id):
    plan = get_object_or_404(Plan, pk=plan_id, is_active=True)

    final_amount = plan.price
    coupon = None
    coupon_code = (request.POST.get('coupon_code') or '').strip()
    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code.upper()).first()
        if not coupon or not coupon.is_valid_for_plan(plan):
            messages.warning(request, f'Coupon "{coupon_code}" is invalid or expired for this plan. Proceeding without a discount.')
            coupon = None
        else:
            final_amount = coupon.calculate_discounted_price(plan.price)

    affiliate = None
    affiliate_code = request.session.get(AFFILIATE_SESSION_KEY)
    if affiliate_code:
        affiliate = AffiliatePartner.objects.filter(code=affiliate_code, is_active=True).first()

    order = Order.objects.create(
        user=request.user, plan=plan, coupon=coupon, affiliate=affiliate,
        original_amount=plan.price, amount=final_amount,
    )
    if coupon:
        coupon.increment_usage()

    client = _razorpay_client()
    if client:
        # Real Razorpay flow — amount is in paise.
        razorpay_order = client.order.create({
            'amount': int(final_amount * 100),
            'currency': 'INR',
            'payment_capture': 1,
        })
        order.gateway_order_id = razorpay_order['id']
        order.save()
        return render(request, 'payments/checkout.html', {
            'order': order,
            'plan': plan,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'razorpay_order_id': razorpay_order['id'],
            'amount_paise': int(final_amount * 100),
        })

    # Demo/dev mode: no gateway keys configured — simulate an instant successful payment
    # so the subscription flow can be tested end-to-end without a live Razorpay account.
    order.status = Order.Status.SUCCESS
    order.payment_id = f'DEMO-{order.id}'
    order.save()
    Transaction.objects.create(order=order, transaction_id=order.payment_id, gateway_response={'mode': 'demo'})
    _activate_subscription(order)
    _credit_affiliate_if_any(order)
    messages.success(request, 'Demo payment successful — no real payment gateway is configured yet. Your subscription is now active.')
    return redirect('payments:success', order_id=order.id)


@csrf_exempt
@login_required
def payment_callback(request, order_id):
    """Handles the redirect/callback from Razorpay after a real payment attempt."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    client = _razorpay_client()

    if request.method == 'POST' and client:
        params = {
            'razorpay_order_id': request.POST.get('razorpay_order_id'),
            'razorpay_payment_id': request.POST.get('razorpay_payment_id'),
            'razorpay_signature': request.POST.get('razorpay_signature'),
        }
        try:
            client.utility.verify_payment_signature(params)
            order.status = Order.Status.SUCCESS
            order.payment_id = params['razorpay_payment_id']
            order.save()
            Transaction.objects.create(order=order, transaction_id=order.payment_id, gateway_response=params)
            _activate_subscription(order)
            _credit_affiliate_if_any(order)
            messages.success(request, 'Payment successful! Your subscription is now active.')
        except Exception:
            order.status = Order.Status.FAILED
            order.save()
            messages.error(request, 'Payment verification failed. Please try again or contact support.')

    return redirect('payments:success', order_id=order.id)


def _activate_subscription(order):
    """Creates/extends the user's subscription and flags them as premium."""
    existing = UserSubscription.objects.filter(user=order.user, plan=order.plan, is_active=True).order_by('-end_date').first()
    start_base = existing.end_date if existing and existing.end_date >= timezone.now().date() else timezone.now().date()
    end_date = start_base + timedelta(days=order.plan.duration_days)

    UserSubscription.objects.create(user=order.user, plan=order.plan, end_date=end_date, is_active=True)
    order.user.is_premium = True
    order.user.save(update_fields=['is_premium'])


def _credit_affiliate_if_any(order):
    """Pays out commission to the referring affiliate partner, if this order came through one."""
    if order.affiliate:
        order.affiliate.record_referred_order(order.amount)


@login_required
def success(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'payments/success.html', {'order': order})


@login_required
def affiliate_dashboard(request):
    """Self-service earnings view for a logged-in affiliate partner — their own stats only."""
    partner = AffiliatePartner.objects.filter(user=request.user).first()
    if not partner:
        messages.info(request, "You're not registered as an affiliate partner yet. Contact support to join the program.")
        return redirect('dashboard:home')
    return render(request, 'payments/affiliate_dashboard.html', {'partner': partner})
