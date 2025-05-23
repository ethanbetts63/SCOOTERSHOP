# payments/urls.py
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
]