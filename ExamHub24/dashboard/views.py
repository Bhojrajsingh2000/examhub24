from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from accounts.models import User
from analytics.models import PerformanceAnalytics
from core.pagination import paginate
from current_affairs.models import CurrentAffair
from mock_tests.models import MockTest
from notifications.models import Notification
from payments.models import Order
from results.models import TestAttempt


@login_required
def home(request):
    """Student dashboard — snapshot of upcoming tests, recent results, and performance."""
    user = request.user

    recent_attempts = TestAttempt.objects.filter(
        user=user, status__in=[TestAttempt.Status.COMPLETED, TestAttempt.Status.AUTO_SUBMITTED]
    ).select_related('test')[:5]

    in_progress = TestAttempt.objects.filter(user=user, status=TestAttempt.Status.IN_PROGRESS).select_related('test')

    performance = PerformanceAnalytics.objects.filter(user=user).select_related('subject')

    unread_notifications = Notification.objects.filter(user=user, is_read=False)[:5]

    latest_affairs = CurrentAffair.objects.published().order_by('-date')[:3]

    total_attempts = TestAttempt.objects.filter(
        user=user, status__in=[TestAttempt.Status.COMPLETED, TestAttempt.Status.AUTO_SUBMITTED]
    ).count()
    avg_accuracy = 0
    if performance:
        avg_accuracy = round(sum(p.avg_score for p in performance) / len(performance), 2)

    recommendations = _build_recommendations(performance)

    context = {
        'recent_attempts': recent_attempts,
        'in_progress': in_progress,
        'performance': performance,
        'unread_notifications': unread_notifications,
        'latest_affairs': latest_affairs,
        'total_attempts': total_attempts,
        'avg_accuracy': avg_accuracy,
        'has_active_subscription': user.has_active_subscription(),
        'recommendations': recommendations,
    }
    return render(request, 'dashboard/student_dashboard.html', context)


def _build_recommendations(performance_records):
    """
    Turns each PerformanceAnalytics.weak_topics string (comma-separated tag names, set
    by analytics.models.PerformanceAnalytics.recalculate_for_user) into a list of
    practiceable recommendations: (subject, tag_name, tag_id_or_None). Falls back to a
    subject-level (no specific tag) recommendation if the weak topic name doesn't match
    any existing QuestionTag — still useful, just less targeted.
    """
    from questions.models import QuestionTag

    recommendations = []
    for record in performance_records:
        if not record.weak_topics:
            continue
        for tag_name in [t.strip() for t in record.weak_topics.split(',') if t.strip()][:3]:  # cap at 3 per subject
            tag = QuestionTag.objects.filter(name=tag_name).first()
            recommendations.append({
                'subject': record.subject,
                'topic_name': tag_name,
                'tag_id': tag.id if tag else None,
            })
    return recommendations[:6]  # cap the whole dashboard widget at 6 suggestions


@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    """Simple admin overview — Django's own admin panel remains the primary content-management tool."""
    from datetime import timedelta
    from django.utils import timezone
    from subscriptions.models import UserSubscription

    today = timezone.now().date()
    month_start = today.replace(day=1)

    total_users = User.objects.count()
    total_premium_users = User.objects.filter(is_premium=True).count()
    total_tests_conducted = TestAttempt.objects.filter(
        status__in=[TestAttempt.Status.COMPLETED, TestAttempt.Status.AUTO_SUBMITTED]
    ).count()
    total_revenue = sum(o.amount for o in Order.objects.filter(status=Order.Status.SUCCESS))
    active_tests = MockTest.objects.filter(is_active=True).count()
    recent_orders = Order.objects.filter(status=Order.Status.SUCCESS).select_related('user', 'plan')[:10]

    # --- Revenue analytics ---
    revenue_this_month = sum(
        o.amount for o in Order.objects.filter(status=Order.Status.SUCCESS, created_at__date__gte=month_start)
    )
    active_subs = UserSubscription.objects.filter(is_active=True, end_date__gte=today).select_related('plan')
    active_subscriptions_count = active_subs.count()
    # MRR: each active subscription's price normalized to a 30-day value, summed —
    # standard approximation for comparing plans of different lengths (monthly/quarterly/yearly).
    mrr = sum((s.plan.price / s.plan.duration_days) * 30 for s in active_subs if s.plan.duration_days)

    churned_this_month = UserSubscription.objects.filter(
        is_active=False, end_date__gte=month_start, end_date__lte=today,
    ).count()
    churn_denominator = active_subscriptions_count + churned_this_month
    churn_rate = round((churned_this_month / churn_denominator * 100), 1) if churn_denominator else 0

    context = {
        'total_users': total_users,
        'total_premium_users': total_premium_users,
        'total_tests_conducted': total_tests_conducted,
        'total_revenue': total_revenue,
        'active_tests': active_tests,
        'recent_orders': recent_orders,
        'revenue_this_month': revenue_this_month,
        'mrr': round(mrr, 2),
        'active_subscriptions_count': active_subscriptions_count,
        'churn_rate': churn_rate,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@user_passes_test(lambda u: u.is_staff)
def admin_activity_log(request):
    """
    Shows who changed what in the admin panel — powered by Django's built-in LogEntry
    model, which every admin.site.* add/change/delete action already writes to
    automatically. No new model or extra tracking code needed.
    """
    entries = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')
    page_obj = paginate(request, entries, per_page=30)
    return render(request, 'dashboard/admin_activity_log.html', {'page_obj': page_obj, 'entries': page_obj.object_list})
