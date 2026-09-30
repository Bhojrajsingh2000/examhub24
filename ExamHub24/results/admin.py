from django.contrib import admin

from .models import AnswerResponse, TestAttempt


class AnswerResponseInline(admin.TabularInline):
    model = AnswerResponse
    extra = 0
    readonly_fields = ('question', 'selected_option', 'is_correct', 'marks_awarded')
    can_delete = False


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'status', 'total_score', 'accuracy', 'rank', 'start_time')
    list_filter = ('status', 'test')
    search_fields = ('user__username', 'test__title')
    readonly_fields = ('total_score', 'correct_count', 'wrong_count', 'unattempted_count', 'accuracy', 'rank')
    inlines = [AnswerResponseInline]
