from django.contrib import admin

from core.cache_utils import clear_home_cache

from .models import Exam, ExamCategory, Subject, SyllabusTopic


class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 1


class SyllabusTopicInline(admin.TabularInline):
    model = SyllabusTopic
    extra = 3


@admin.register(ExamCategory)
class ExamCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        clear_home_cache()  # homepage shows the top 8 active categories

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        clear_home_cache()


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'exam_date', 'is_active')
    list_filter = ('category', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    inlines = [SubjectInline]


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'exam')
    list_filter = ('exam',)
    search_fields = ('name',)
    inlines = [SyllabusTopicInline]
