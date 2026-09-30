from django.urls import path

from . import views

app_name = 'results'

urlpatterns = [
    path('attempt/<int:attempt_id>/', views.result_detail, name='result_detail'),
    path('history/', views.result_history, name='result_history'),
    path('leaderboard/<int:test_id>/', views.leaderboard, name='leaderboard'),
    path('weekly-leaderboard/', views.weekly_leaderboard, name='weekly_leaderboard'),
]
