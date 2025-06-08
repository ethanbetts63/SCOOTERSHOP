# payments/urls.py
from django.urls import path
from . import views
from .views import Refunds # This already imports the HireRefunds package
from .utils import ajax_get_service_booking_details, ajax_get_hire_booking_details
# Import the new ProcessHireRefundView directly


app_name = 'payments'

urlpatterns = [
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    # New URL for fetching hire booking details via AJAX
    path('api/hire-booking-details/<int:pk>/', Refunds.utils.get_hire_booking_details_json, name='api_hire_booking_details'),
    path('api/service-booking-details/<int:pk>/', ajax_get_service_booking_details.get_service_booking_details_json, name='api_service_booking_details'),
    
    path('refund/request/', Refunds.UserRefundRequestView.as_view(), name='user_refund_request_hire'),
    path('refund/request/confirmation/', Refunds.UserConfirmationRefundRequestView.as_view(), name='user_confirmation_refund_request'),

    # User page after clicking the verification link in email
    path('refund/verified/', Refunds.UserVerifiedRefundView.as_view(), name='user_verified_refund'),
    # URL for the email verification link (e.g., /refund/verify/?token=...)
    path('refund/verify/', Refunds.UserVerifyRefundView.as_view(), name='user_verify_refund'),
]
