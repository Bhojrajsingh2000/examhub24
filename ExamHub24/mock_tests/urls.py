from django.urls import path

from . import views

app_name = 'mock_tests'

urlpatterns = [
    path('', views.series_list, name='series_list'),
    path('series/<int:pk>/', views.series_detail, name='series_detail'),
    path('test/<int:pk>/instructions/', views.test_instructions, name='test_instructions'),
    path('test/<int:pk>/start/', views.start_test, name='start_test'),
    path('attempt/<int:attempt_id>/', views.attempt_test, name='attempt_test'),
    path('attempt/<int:attempt_id>/save-answer/', views.save_answer, name='save_answer'),
    path('attempt/<int:attempt_id>/submit/', views.submit_test, name='submit_test'),
    path('sectional/<int:subject_id>/', views.sectional_test_builder, name='sectional_test_builder'),
]
