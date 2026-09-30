from django.urls import path

from . import views

app_name = 'current_affairs'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('<int:pk>/', views.detail, name='detail'),
]
