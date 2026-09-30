from django.urls import path

from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('', views.plans, name='plans'),
    path('<int:pk>/', views.plan_detail, name='plan_detail'),
    path('<int:pk>/start-trial/', views.start_trial, name='start_trial'),
]
