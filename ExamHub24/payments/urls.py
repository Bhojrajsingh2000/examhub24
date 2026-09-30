from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('create-order/<int:plan_id>/', views.create_order, name='create_order'),
    path('callback/<int:order_id>/', views.payment_callback, name='payment_callback'),
    path('success/<int:order_id>/', views.success, name='success'),
    path('go/<str:code>/', views.affiliate_link, name='affiliate_link'),
    path('affiliate/dashboard/', views.affiliate_dashboard, name='affiliate_dashboard'),
]
