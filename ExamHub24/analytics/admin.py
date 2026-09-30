from django.contrib import admin

from .models import PerformanceAnalytics


@admin.register(PerformanceAnalytics)
class PerformanceAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'attempts_count', 'avg_score', 'last_updated')
    list_filter = ('subject',)
    search_fields = ('user__username',)
    readonly_fields = ('attempts_count', 'avg_score', 'weak_topics', 'strong_topics', 'last_updated')
