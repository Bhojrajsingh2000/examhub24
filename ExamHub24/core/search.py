from django.db.models import Q
from django.shortcuts import render

from current_affairs.models import CurrentAffair
from exams.models import Exam
from mock_tests.models import TestSeries
from study_material.models import StudyMaterial


def site_search(request):
    """
    One search box (navbar) across the content types students actually look things up
    by: exams, test series, current affairs, and study material. Deliberately excludes
    Question (not a public-facing model) and user accounts.
    """
    query = request.GET.get('q', '').strip()
    results = {'exams': [], 'test_series': [], 'current_affairs': [], 'study_material': []}

    if query:
        results['exams'] = Exam.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query), is_active=True
        ).select_related('category')[:10]

        results['test_series'] = TestSeries.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).select_related('exam')[:10]

        results['current_affairs'] = CurrentAffair.objects.published().filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )[:10]

        results['study_material'] = StudyMaterial.objects.filter(
            title__icontains=query
        ).select_related('subject')[:10]

    total_results = sum(len(v) for v in results.values())

    return render(request, 'core/search_results.html', {
        'query': query, 'results': results, 'total_results': total_results,
    })
