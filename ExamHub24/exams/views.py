from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from mock_tests.models import TestSeries

from .models import Exam, ExamCategory, Subject, SyllabusTopic, UserTopicProgress


def category_list(request):
    categories = ExamCategory.objects.filter(is_active=True)
    return render(request, 'exams/category_list.html', {'categories': categories})


def exam_list(request, category_slug):
    category = get_object_or_404(ExamCategory, slug=category_slug, is_active=True)
    exams = category.exams.filter(is_active=True)
    return render(request, 'exams/exam_list.html', {'category': category, 'exams': exams})


def exam_detail(request, exam_slug):
    exam = get_object_or_404(Exam, slug=exam_slug, is_active=True)
    subjects = exam.subjects.all()
    test_series = TestSeries.objects.filter(exam=exam)
    return render(request, 'exams/exam_detail.html', {
        'exam': exam,
        'subjects': subjects,
        'test_series': test_series,
    })


@login_required
def syllabus_checklist(request, exam_slug):
    """
    Shows every syllabus topic for the exam, grouped by subject, with a checkbox for
    each — lets a student track what they've studied. Progress bars are computed
    per-subject and overall.
    """
    exam = get_object_or_404(Exam, slug=exam_slug, is_active=True)
    subjects = exam.subjects.prefetch_related('syllabus_topics').all()

    completed_topic_ids = set(
        UserTopicProgress.objects.filter(user=request.user, topic__subject__exam=exam, is_completed=True)
        .values_list('topic_id', flat=True)
    )

    subject_data = []
    total_topics = 0
    total_completed = 0
    for subject in subjects:
        topics = list(subject.syllabus_topics.all())
        completed = sum(1 for t in topics if t.id in completed_topic_ids)
        total_topics += len(topics)
        total_completed += completed
        subject_data.append({
            'subject': subject,
            'topics': topics,
            'completed_topic_ids': completed_topic_ids,
            'progress_pct': round((completed / len(topics) * 100), 0) if topics else 0,
        })

    overall_pct = round((total_completed / total_topics * 100), 0) if total_topics else 0

    return render(request, 'exams/syllabus_checklist.html', {
        'exam': exam,
        'subject_data': subject_data,
        'overall_pct': overall_pct,
        'total_topics': total_topics,
        'total_completed': total_completed,
    })


@login_required
@require_POST
def toggle_topic_progress(request, topic_id):
    """AJAX endpoint: flips a syllabus topic between studied/not-studied for the current user."""
    from django.utils import timezone

    topic = get_object_or_404(SyllabusTopic, pk=topic_id)
    progress, _ = UserTopicProgress.objects.get_or_create(user=request.user, topic=topic)
    progress.is_completed = not progress.is_completed
    progress.completed_at = timezone.now() if progress.is_completed else None
    progress.save()
    return JsonResponse({'is_completed': progress.is_completed})
