from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.pagination import paginate

from .models import TestAttempt
from .services import leaderboard_cache_key

LEADERBOARD_CACHE_TTL = 60  # seconds — short TTL since scores change as students submit
WEEKLY_LEADERBOARD_CACHE_TTL = 300  # 5 min — aggregate query is heavier, changes less urgently


@login_required
def result_detail(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, pk=attempt_id, user=request.user)
    responses = attempt.responses.select_related('question').order_by('question__id')
    total_attempters = TestAttempt.objects.filter(
        test=attempt.test, status__in=[TestAttempt.Status.COMPLETED, TestAttempt.Status.AUTO_SUBMITTED]
    ).count()

    from questions.models import BookmarkedQuestion
    bookmarked_qids = set(
        BookmarkedQuestion.objects.filter(user=request.user, question__in=[r.question_id for r in responses])
        .values_list('question_id', flat=True)
    )

    return render(request, 'results/result_detail.html', {
        'attempt': attempt,
        'responses': responses,
        'total_attempters': total_attempters,
        'bookmarked_qids': bookmarked_qids,
    })


@login_required
def result_history(request):
    attempts = TestAttempt.objects.filter(
        user=request.user,
        status__in=[TestAttempt.Status.COMPLETED, TestAttempt.Status.AUTO_SUBMITTED],
    ).select_related('test')
    page_obj = paginate(request, attempts, per_page=15)
    return render(request, 'results/result_history.html', {'page_obj': page_obj, 'attempts': page_obj.object_list})


@login_required
def leaderboard(request, test_id):
    cache_key = leaderboard_cache_key(test_id)
    top_attempts_list = cache.get(cache_key)
    if top_attempts_list is None:
        top_attempts_list = list(
            TestAttempt.objects.filter(
                test_id=test_id,
                status__in=[TestAttempt.Status.COMPLETED, TestAttempt.Status.AUTO_SUBMITTED],
            ).select_related('user', 'test').order_by('rank')
        )
        cache.set(cache_key, top_attempts_list, LEADERBOARD_CACHE_TTL)

    page_obj = paginate(request, top_attempts_list, per_page=50)
    return render(request, 'results/leaderboard.html', {'page_obj': page_obj, 'top_attempts': page_obj.object_list})


@login_required
def weekly_leaderboard(request):
    """
    Cross-test leaderboard: total score summed across every test a student attempted in
    the last 7 days. Rewards consistent practice, not just one strong test — a different
    signal than the per-test leaderboard above.
    """
    cache_key = 'weekly_leaderboard_v1'
    rows = cache.get(cache_key)
    if rows is None:
        cutoff = timezone.now() - timedelta(days=7)
        rows = list(
            TestAttempt.objects.filter(
                status__in=[TestAttempt.Status.COMPLETED, TestAttempt.Status.AUTO_SUBMITTED],
                end_time__gte=cutoff,
            )
            .values('user_id', 'user__username', 'user__full_name')
            .annotate(total_score=Sum('total_score'), tests_taken=Count('id'))
            .order_by('-total_score')
        )
        cache.set(cache_key, rows, WEEKLY_LEADERBOARD_CACHE_TTL)

    for i, row in enumerate(rows, start=1):
        row['rank'] = i

    page_obj = paginate(request, rows, per_page=50)
    return render(request, 'results/weekly_leaderboard.html', {'page_obj': page_obj, 'rows': page_obj.object_list})
