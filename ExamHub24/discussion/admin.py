from django.contrib import admin

from .models import Discussion


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'comment_preview', 'is_flagged', 'created_at')
    list_filter = ('is_flagged',)
    search_fields = ('comment', 'user__username')
    actions = ['clear_flag', 'delete_flagged']

    def comment_preview(self, obj):
        return obj.comment[:60]

    @admin.action(description='Clear flag (mark as reviewed, not a problem)')
    def clear_flag(self, request, queryset):
        queryset.update(is_flagged=False)

    @admin.action(description='Delete selected comments')
    def delete_flagged(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} comment(s) deleted.')
