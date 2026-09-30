import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from results.models import AnswerResponse, TestAttempt
from core.pagination import paginate
from .models import MockTest, TestQuestion, TestSeries


SORT_OPTIONS = {
    'newest': '-created_at',
    'oldest': 'created_at',
    'price_asc': 'price',
    'price_desc': '-price',
}


def series_list(request):
    query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'newest')
    series_type = request.GET.get('type', '').strip()

    all_series = TestSeries.objects.select_related('exam').all()
    if query:
        all_series = all_series.filter(Q(title__icontains=query) | Q(exam__name__icontains=query))
    if series_type in dict(TestSeries.SeriesType.choices):
        all_series = all_series.filter(series_type=series_type)
    all_series = all_series.order_by(SORT_OPTIONS.get(sort, '-created_at'))

    page_obj = paginate(request, all_series, per_page=12)
    return render(request, 'mock_tests/series_list.html', {
        'page_obj': page_obj, 'all_series': page_obj.object_list, 'query': query,
        'sort': sort, 'series_type': series_type, 'series_types': TestSeries.SeriesType.choices,
    })


def series_detail(request, pk):
    series = get_object_or_404(TestSeries, pk=pk)
    # prefetch_related avoids the N+1 queries that MockTest.total_questions/total_marks
    # would otherwise trigger once per test when the template loops over `tests`.
    tests = series.mock_tests.filter(is_active=True).prefetch_related('test_questions__question')
    return render(request, 'mock_tests/series_detail.html', {'series': series, 'tests': tests})


@login_required
def test_instructions(request, pk):
    test = get_object_or_404(MockTest, pk=pk, is_active=True)
    can_access = test.is_free_to_access(request.user)
    is_upcoming = bool(test.start_date and timezone.now() < test.start_date)
    return render(request, 'mock_tests/test_instructions.html', {
        'test': test, 'can_access': can_access, 'is_live': test.is_live(), 'is_upcoming': is_upcoming,
    })


@login_required
def start_test(request, pk):
    test = get_object_or_404(MockTest, pk=pk, is_active=True)

    if not test.is_live():
        # Respects MockTest.start_date/end_date — previously these fields were saved but
        # never actually checked, so a scheduled-for-later or already-closed test could
        # still be started at any time. Resuming an already-started attempt is still
        # allowed even if the window just closed, so students don't lose in-progress work.
        already_started = TestAttempt.objects.filter(user=request.user, test=test, status='in_progress').exists()
        if not already_started:
            if test.start_date and timezone.now() < test.start_date:
                messages.warning(request, f'This test opens on {test.start_date:%d %b %Y, %I:%M %p}.')
            else:
                messages.warning(request, 'This test window has closed.')
            return redirect('mock_tests:test_instructions', pk=test.id)

    if not test.is_free_to_access(request.user):
        messages.warning(request, 'This test is part of a premium series. Please subscribe to access it.')
        return redirect('subscriptions:plans')

    # Resume an in-progress attempt if one already exists, otherwise start a new one.
    attempt = TestAttempt.objects.filter(user=request.user, test=test, status='in_progress').first()
    if not attempt:
        attempt = TestAttempt.objects.create(user=request.user, test=test, status='in_progress')

    return redirect('mock_tests:attempt_test', attempt_id=attempt.id)


@login_required
def attempt_test(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, pk=attempt_id, user=request.user)
    if attempt.status != 'in_progress':
        return redirect('results:result_detail', attempt_id=attempt.id)

    test_questions = attempt.test.test_questions.select_related('question').all()

    # Ensure an AnswerResponse placeholder exists per question (so navigation/status works from the start).
    existing_qids = set(attempt.responses.values_list('question_id', flat=True))
    new_responses = [
        AnswerResponse(attempt=attempt, question=tq.question)
        for tq in test_questions if tq.question_id not in existing_qids
    ]
    if new_responses:
        AnswerResponse.objects.bulk_create(new_responses)

    responses_by_qid = {r.question_id: r for r in attempt.responses.all()}

    elapsed_seconds = (timezone.now() - attempt.start_time).total_seconds()
    remaining_seconds = max(0, attempt.test.duration_minutes * 60 - int(elapsed_seconds))

    context = {
        'attempt': attempt,
        'test': attempt.test,
        'test_questions': test_questions,
        'responses_by_qid': responses_by_qid,
        'remaining_seconds': remaining_seconds,
    }
    return render(request, 'mock_tests/attempt_test.html', context)


@login_required
@require_POST
def save_answer(request, attempt_id):
    """AJAX endpoint: saves/updates a single answer as the student progresses through the test."""
    attempt = get_object_or_404(TestAttempt, pk=attempt_id, user=request.user, status='in_progress')
    data = json.loads(request.body or '{}')
    question_id = data.get('question_id')
    selected_option = data.get('selected_option') or None

    response, _ = AnswerResponse.objects.get_or_create(attempt=attempt, question_id=question_id)
    response.selected_option = selected_option
    response.save()
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def submit_test(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, pk=attempt_id, user=request.user, status='in_progress')
    auto = request.POST.get('auto') == '1'

    from results.services import finalize_and_notify
    finalize_and_notify(attempt, auto_submitted=auto)

    messages.success(request, 'Test submitted successfully!')
    return redirect('results:result_detail', attempt_id=attempt.id)


@login_required
def sectional_test_builder(request, subject_id):
    """Self-serve form: pick topics (tags) + question count + duration, generate a test on the spot."""
    from exams.models import Subject
    from questions.models import QuestionTag
    from .sectional import generate_sectional_test

    subject = get_object_or_404(Subject, pk=subject_id)
    available_tags = QuestionTag.objects.filter(questions__subject=subject).distinct()

    if request.method == 'POST':
        tag_ids = request.POST.getlist('tags')
        tags = list(available_tags.filter(id__in=tag_ids)) if tag_ids else []
        try:
            question_count = max(1, min(50, int(request.POST.get('question_count', 10))))
            duration_minutes = max(2, min(120, int(request.POST.get('duration_minutes', 15))))
        except ValueError:
            question_count, duration_minutes = 10, 15

        test = generate_sectional_test(request.user, subject, tags, question_count, duration_minutes)
        if not test:
            messages.warning(request, 'Not enough questions are available for that selection yet. Try fewer topics or a lower question count.')
            return redirect('mock_tests:sectional_test_builder', subject_id=subject.id)

        return redirect('mock_tests:test_instructions', pk=test.id)

    preselected_tag_id = request.GET.get('tag')
    try:
        preselected_tag_id = int(preselected_tag_id) if preselected_tag_id else None
    except ValueError:
        preselected_tag_id = None

    return render(request, 'mock_tests/sectional_test_builder.html', {
        'subject': subject, 'available_tags': available_tags, 'preselected_tag_id': preselected_tag_id,
    })
