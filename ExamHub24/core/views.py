from django.contrib import messages
from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import get_template

from exams.models import ExamCategory
from current_affairs.models import CurrentAffair
from mock_tests.models import TestSeries

HOME_CACHE_KEY = 'home_page_context_v1'
HOME_CACHE_TTL = 300  # 5 minutes — homepage content (categories/free series/affairs) changes rarely


def home(request):
    """Landing page: exam categories, popular free test series, latest current affairs.

    Cached for HOME_CACHE_TTL seconds since every visitor (including anonymous ones) hits
    this page and its 3 queries rarely need to be fresh-to-the-second. New content (e.g. a
    newly published current affair) will appear within 5 minutes rather than instantly —
    an admin can also call core.cache_utils.clear_home_cache() manually if needed sooner.
    """
    cached = cache.get(HOME_CACHE_KEY)
    if cached is not None:
        return render(request, 'core/home.html', cached)

    context = {
        'categories': list(ExamCategory.objects.filter(is_active=True)[:8]),
        'free_series': list(TestSeries.objects.filter(is_free=True).select_related('exam')[:6]),
        'latest_affairs': list(CurrentAffair.objects.published().order_by('-date')[:5]),
    }
    cache.set(HOME_CACHE_KEY, context, HOME_CACHE_TTL)
    return render(request, 'core/home.html', context)


def about(request):
    return render(request, 'core/about.html')


def contact(request):
    if request.method == 'POST':
        # In production: save to a Feedback/ContactMessage model and/or send an email.
        messages.success(request, 'Thanks for reaching out! We will get back to you soon.')
        return redirect('core:contact')
    return render(request, 'core/contact.html')


def health_check(request):
    """
    Lightweight health-check endpoint for uptime monitors (e.g. UptimeRobot) and load
    balancers. Checks basic DB connectivity so a broken database shows up as unhealthy
    instead of a generic 500. Returns 200 + {"status": "ok"} when healthy, 503 otherwise.
    Deliberately has no auth and does no heavy work — monitors may call this every minute.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=503)


def service_worker_view(request):
    """
    Serves the service worker JS from the SITE ROOT (see project urls.py — this view is
    wired to /service-worker.js, not /static/service-worker.js). A service worker can
    only control pages within its own scope and below, so root-serving it is what lets
    it manage the whole site rather than just the /static/ folder.
    """
    template = get_template('core/service_worker.js')
    return HttpResponse(template.render({}, request), content_type='application/javascript')


def offline_view(request):
    """Fallback page the service worker shows when a navigation fails with no network."""
    return render(request, 'core/offline.html')
