from django.contrib import admin

from .models import AffiliatePartner, Order, Transaction


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'plan', 'coupon', 'affiliate', 'original_amount', 'amount', 'status', 'created_at')
    list_filter = ('status', 'plan', 'coupon', 'affiliate')
    search_fields = ('user__username', 'payment_id', 'gateway_order_id')
    actions = ['refund_orders']

    @admin.action(description='Refund selected orders (revokes their subscription access)')
    def refund_orders(self, request, queryset):
        from .services import process_refund

        count = 0
        for order in queryset.filter(status=Order.Status.SUCCESS):
            if process_refund(order, reason=f'Refunded by {request.user} via admin panel'):
                count += 1
        self.message_user(request, f'{count} order(s) refunded and access revoked.')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('order', 'transaction_id', 'timestamp')


@admin.register(AffiliatePartner)
class AffiliatePartnerAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'commission_percent', 'total_referred_orders', 'total_earned', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'code')
    readonly_fields = ('total_earned', 'total_referred_orders')
