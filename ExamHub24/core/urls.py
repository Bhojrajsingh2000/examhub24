from django.urls import path
from . import views
from .search import site_search

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('search/', site_search, name='search'),
    path('health/', views.health_check, name='health_check'),
    path('service-worker.js', views.service_worker_view, name='service_worker'),
    path('offline/', views.offline_view, name='offline'),
]
