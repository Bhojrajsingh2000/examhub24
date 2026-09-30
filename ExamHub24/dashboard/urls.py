from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('admin-overview/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-activity-log/', views.admin_activity_log, name='admin_activity_log'),
]
