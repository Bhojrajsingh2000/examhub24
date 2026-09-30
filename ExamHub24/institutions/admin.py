from django.contrib import admin

from .models import Institution


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'admin_user', 'student_count', 'max_students', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
