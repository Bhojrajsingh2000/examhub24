"""
Refund handling. Kept separate from models.py/admin.py so the same logic can be called
from the admin action (payments/admin.py) and, if a real gateway's refund webhook is
added later, from there too — one place, not duplicated.
"""
from django.utils import timezone


def process_refund(order, reason=''):
    """
    Marks the order as refunded and revokes the subscription it paid for — but only
    downgrades the user from premium if they have no OTHER still-active, still-valid
    subscription (e.g. a separate purchase that hasn't expired).
    """
    from .models import Order

    if order.status == Order.Status.REFUNDED:
        return False  # already refunded — don't double-process

    order.status = Order.Status.REFUNDED
    order.refunded_at = timezone.now()
    order.refund_reason = reason
    order.save(update_fields=['status', 'refunded_at', 'refund_reason'])

    from subscriptions.models import UserSubscription

    # Best-effort match: the subscription created around the same time, for the same
    # user+plan, that's still active. There's no direct FK from UserSubscription back to
    # the Order that paid for it (orders and subscriptions were designed independently),
    # so this is a heuristic, not a guaranteed-exact match — fine for a demo/small-scale
    # system, but note this limitation if wiring up a real gateway's refund webhook.
    matching_sub = (
        UserSubscription.objects.filter(user=order.user, plan=order.plan, is_active=True)
        .order_by('-start_date').first()
    )
    if matching_sub:
        matching_sub.is_active = False
        matching_sub.save(update_fields=['is_active'])

    today = timezone.now().date()
    still_has_access = UserSubscription.objects.filter(user=order.user, is_active=True, end_date__gte=today).exists()
    if not still_has_access:
        order.user.is_premium = False
        order.user.save(update_fields=['is_premium'])

    return True
