from django.contrib import admin
from django.urls import path
from django.utils.html import format_html

from .models import BookmarkedQuestion, Question, QuestionTag


@admin.register(QuestionTag)
class QuestionTagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'subject', 'difficulty_level', 'correct_option', 'marks', 'is_active', 'preview_link')
    list_filter = ('subject', 'difficulty_level', 'is_active')
    search_fields = ('question_text',)
    filter_horizontal = ('tags',)
    actions = ['deactivate_questions', 'activate_questions']
    fieldsets = (
        (None, {'fields': ('subject', 'question_text', 'question_image')}),
        ('Options', {'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_option')}),
        ('Metadata', {'fields': ('explanation', 'video_solution_url', 'difficulty_level', 'marks', 'negative_marks', 'tags', 'created_by', 'is_active')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def preview_link(self, obj):
        if not obj.pk:
            return '—'
        return format_html('<a href="{}" target="_blank">Preview</a>', f'{obj.pk}/preview/')
    preview_link.short_description = 'Student view'

    def get_urls(self):
        # Adds a read-only "how will students actually see this?" preview, reachable only
        # from within the admin (staff-only via admin's own login), without needing a
        # public-facing URL/view. Catches formatting mistakes — e.g. a garbled image, an
        # option that's visually identical to another — before students ever see them.
        custom_urls = [
            path('<int:question_id>/preview/', self.admin_site.admin_view(self.preview_view), name='questions_question_preview'),
        ]
        return custom_urls + super().get_urls()

    def preview_view(self, request, question_id):
        from django.shortcuts import get_object_or_404, render
        question = get_object_or_404(Question, pk=question_id)
        return render(request, 'questions/admin_preview.html', {'question': question})

    @admin.action(description='Deactivate selected questions (safe alternative to deleting)')
    def deactivate_questions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} question(s) deactivated. They will no longer appear in new tests, '
                                    f'but existing results referencing them are preserved.')

    @admin.action(description='Re-activate selected questions')
    def activate_questions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} question(s) re-activated.')


@admin.register(BookmarkedQuestion)
class BookmarkedQuestionAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'created_at')
    search_fields = ('user__username',)
