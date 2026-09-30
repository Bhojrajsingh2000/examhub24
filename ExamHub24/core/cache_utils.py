from django.core.cache import cache


def clear_home_cache():
    """
    Call this after saving/deleting an ExamCategory, TestSeries, or CurrentAffair from
    code (the admin panel already calls it automatically — see each app's admin.py) so
    the homepage reflects the change immediately instead of waiting for the cache TTL
    to expire (see core/views.py HOME_CACHE_TTL).
    """
    cache.delete('home_page_context_v1')
