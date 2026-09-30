from django.contrib import admin

from .models import StudyMaterial, VideoLecture


@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'material_type', 'is_premium', 'download_count')
    list_filter = ('subject', 'material_type', 'is_premium')
    search_fields = ('title',)

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.uploaded_by:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(VideoLecture)
class VideoLectureAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'duration', 'is_premium')
    list_filter = ('subject', 'is_premium')
