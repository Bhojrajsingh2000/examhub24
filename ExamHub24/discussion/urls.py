from django.urls import path

from . import views

app_name = 'discussion'

urlpatterns = [
    path('question/<int:question_id>/', views.question_discussion, name='question_discussion'),
    path('question/<int:question_id>/post/', views.post_comment, name='post_comment'),
    path('comment/<int:discussion_id>/like/', views.toggle_like, name='toggle_like'),
    path('comment/<int:discussion_id>/flag/', views.flag_comment, name='flag_comment'),
]
