from django.urls import path

from . import views

app_name = 'institutions'

urlpatterns = [
    path('<int:institution_id>/dashboard/', views.institution_dashboard, name='institution_dashboard'),
]
