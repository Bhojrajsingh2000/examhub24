from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Plan, UserSubscription


def plans(request):
    all_plans = Plan.objects.filter(is_active=True)
    active_sub = None
    if request.user.is_authenticated:
        active_sub = request.user.subscriptions.filter(is_active=True).order_by('-end_date').first()
    return render(request, 'subscriptions/plans.html', {'plans': all_plans, 'active_sub': active_sub})


def _is_trial_eligible(user):
    """A user is only eligible for a free trial if they've never had ANY subscription before (paid or trial)."""
    return not UserSubscription.objects.filter(user=user).exists()


@login_required
def plan_detail(request, pk):
    plan = get_object_or_404(Plan, pk=pk, is_active=True)
    trial_eligible = plan.trial_days > 0 and _is_trial_eligible(request.user)
    return render(request, 'subscriptions/plan_detail.html', {'plan': plan, 'trial_eligible': trial_eligible})


@login_required
def start_trial(request, pk):
    from datetime import timedelta
    from django.utils import timezone

    plan = get_object_or_404(Plan, pk=pk, is_active=True)

    if plan.trial_days <= 0 or not _is_trial_eligible(request.user):
        messages.warning(request, 'You are not eligible for a free trial of this plan.')
        return redirect('subscriptions:plan_detail', pk=plan.id)

    UserSubscription.objects.create(
        user=request.user, plan=plan, end_date=timezone.now().date() + timedelta(days=plan.trial_days), is_active=True,
    )
    request.user.is_premium = True
    request.user.save(update_fields=['is_premium'])

    messages.success(request, f'Your {plan.trial_days}-day free trial of {plan.name} has started!')
    return redirect('dashboard:home')
