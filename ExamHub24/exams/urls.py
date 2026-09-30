from django.urls import path

from . import views

app_name = 'exams'

urlpatterns = [
    path('', views.category_list, name='category_list'),
    path('category/<slug:category_slug>/', views.exam_list, name='exam_list'),
    path('syllabus/<slug:exam_slug>/', views.syllabus_checklist, name='syllabus_checklist'),
    path('syllabus/topic/<int:topic_id>/toggle/', views.toggle_topic_progress, name='toggle_topic_progress'),
    path('<slug:exam_slug>/', views.exam_detail, name='exam_detail'),
]
