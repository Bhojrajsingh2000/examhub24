from django.contrib import admin

from core.cache_utils import clear_home_cache

from .models import MockTest, TestQuestion, TestSeries


class TestQuestionInline(admin.TabularInline):
    model = TestQuestion
    extra = 1
    autocomplete_fields = ['question']


@admin.register(TestSeries)
class TestSeriesAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam', 'series_type', 'is_free', 'price', 'validity_days')
    list_filter = ('exam', 'series_type', 'is_free')
    search_fields = ('title',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        clear_home_cache()  # homepage shows the 6 latest free series

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        clear_home_cache()


@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ('title', 'series', 'duration_minutes', 'total_questions', 'is_active', 'generated_by')
    list_filter = ('series', 'is_active')
    search_fields = ('title',)
    inlines = [TestQuestionInline]
    actions = ['deactivate_tests']

    @admin.action(description='Deactivate selected tests (safe alternative to deleting)')
    def deactivate_tests(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} test(s) deactivated and hidden from students. '
                                    f'Existing results/leaderboards referencing them are preserved.')
