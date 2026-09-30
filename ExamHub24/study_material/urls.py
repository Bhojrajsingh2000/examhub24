from django.urls import path

from . import views

app_name = 'study_material'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('download/<int:pk>/', views.download, name='download'),
]
