from django.urls import path

from . import views

app_name = 'questions'

urlpatterns = [
    path('bookmarks/', views.bookmark_list, name='bookmark_list'),
    path('bookmarks/<int:question_id>/toggle/', views.bookmark_toggle, name='bookmark_toggle'),
    path('practice/', views.practice_subject_list, name='practice_subject_list'),
    path('practice/<int:subject_id>/', views.practice_session, name='practice_session'),
]
