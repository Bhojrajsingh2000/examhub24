from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Plan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.PositiveIntegerField()
    trial_days = models.PositiveIntegerField(default=0, help_text='Free trial length before the first-ever paid subscription. 0 = no trial.')
    features = models.TextField(help_text='Comma-separated list of features')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return f"{self.name} — Rs. {self.price} / {self.duration_days} days"

    def feature_list(self):
        return [f.strip() for f in self.features.split(',') if f.strip()]


class UserSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.user} - {self.plan.name}"

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = timezone.now().date() + timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)

    def is_valid(self):
        return self.is_active and self.end_date >= timezone.now().date()

    def days_remaining(self):
        delta = self.end_date - timezone.now().date()
        return max(0, delta.days)


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FLAT = 'flat', 'Flat Amount'

    code = models.CharField(max_length=30, unique=True, help_text='Case-insensitive, e.g. WELCOME20')
    discount_type = models.CharField(max_length=12, choices=DiscountType.choices, default=DiscountType.PERCENTAGE)
    discount_value = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal('0'))],
        help_text='For percentage: 0-100. For flat: rupee amount to subtract.',
    )
    applicable_plans = models.ManyToManyField(Plan, blank=True, help_text='Leave empty to apply to all plans.')
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True, help_text='Leave blank for no expiry.')
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text='Leave blank for unlimited uses.')
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code.upper()

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def is_valid_for_plan(self, plan):
        if not self.is_active:
            return False
        now = timezone.now()
        if now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        if self.applicable_plans.exists() and plan not in self.applicable_plans.all():
            return False
        return True

    def calculate_discounted_price(self, price):
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = price * (self.discount_value / Decimal('100'))
        else:
            discount = self.discount_value
        discounted = price - discount
        return max(discounted, Decimal('0'))

    def increment_usage(self):
        self.used_count = models.F('used_count') + 1
        self.save(update_fields=['used_count'])
