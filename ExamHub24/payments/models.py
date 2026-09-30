import random
import string

from django.conf import settings
from django.db import models


class AffiliatePartner(models.Model):
    """
    A partner (blogger, YouTuber, coaching influencer, etc.) who earns a commission on
    subscriptions purchased through their referral link/code — distinct from a Coupon
    (subscriptions.Coupon discounts the customer's price); an affiliate code tracks
    partner earnings and doesn't have to discount anything for the student.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='affiliate_profile')
    code = models.CharField(max_length=20, unique=True, blank=True)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10, help_text='% of each referred order paid to this partner.')
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_referred_orders = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        super().save(*args, **kwargs)

    def record_referred_order(self, order_amount):
        """Called by payments/views.py create_order() on a successful order made through this partner's link."""
        commission = order_amount * (self.commission_percent / 100)
        AffiliatePartner.objects.filter(pk=self.pk).update(
            total_earned=models.F('total_earned') + commission,
            total_referred_orders=models.F('total_referred_orders') + 1,
        )
        return commission


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    plan = models.ForeignKey('subscriptions.Plan', on_delete=models.CASCADE)
    coupon = models.ForeignKey('subscriptions.Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    affiliate = models.ForeignKey(AffiliatePartner, on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_orders')
    original_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text='Plan price before any coupon discount.')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    gateway_order_id = models.CharField(max_length=100, blank=True)
    payment_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user} - {self.status}"


class Transaction(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions')
    gateway_response = models.JSONField(default=dict, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Txn for {self.order}"
