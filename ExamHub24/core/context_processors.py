from django.conf import settings


def site_context(request):
    """Adds site-wide variables to every template's context."""
    context = {
        'SITE_NAME': settings.SITE_NAME,
    }
    if request.user.is_authenticated:
        # Avoids importing subscriptions models at module load time (keeps this decoupled).
        from subscriptions.models import UserSubscription
        active_sub = (
            UserSubscription.objects.filter(user=request.user, is_active=True)
            .order_by('-end_date')
            .first()
        )
        context['active_subscription'] = active_sub
    return context
