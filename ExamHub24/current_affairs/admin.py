from django.contrib import admin

from core.cache_utils import clear_home_cache

from .models import CurrentAffair, DailyQuiz


@admin.register(CurrentAffair)
class CurrentAffairAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'date', 'is_published', 'publish_at')
    list_filter = ('category', 'is_published')
    search_fields = ('title', 'content')
    date_hierarchy = 'date'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        clear_home_cache()  # homepage shows the 5 latest published affairs

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        clear_home_cache()


@admin.register(DailyQuiz)
class DailyQuizAdmin(admin.ModelAdmin):
    list_display = ('date', 'is_active')
    filter_horizontal = ('questions',)
