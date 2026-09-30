from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, render

from .models import Institution


@login_required
def institution_dashboard(request, institution_id):
    """
    Aggregate stats for one institution's students — accessible only to that
    institution's designated admin_user (or any Django staff/superuser, for support).
    """
    institution = get_object_or_404(Institution, pk=institution_id)

    is_owner = institution.admin_user_id == request.user.id
    if not (is_owner or request.user.is_staff):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have access to this institution's dashboard.")

    from results.models import TestAttempt

    student_user_ids = list(institution.students.values_list('user_id', flat=True))
    attempts = TestAttempt.objects.filter(
        user_id__in=student_user_ids,
        status__in=[TestAttempt.Status.COMPLETED, TestAttempt.Status.AUTO_SUBMITTED],
    )

    total_students = len(student_user_ids)
    total_attempts = attempts.count()
    avg_accuracy = attempts.aggregate(avg=Avg('accuracy'))['avg'] or 0
    premium_students = institution.students.filter(user__is_premium=True).count()

    top_performers = (
        attempts.values('user__id', 'user__username', 'user__full_name')
        .annotate(avg_score=Avg('total_score'), tests_taken=Count('id'))
        .order_by('-avg_score')[:10]
    )

    return render(request, 'institutions/dashboard.html', {
        'institution': institution,
        'total_students': total_students,
        'total_attempts': total_attempts,
        'avg_accuracy': round(avg_accuracy, 2),
        'premium_students': premium_students,
        'top_performers': top_performers,
    })
