# hire/urls.py
from django.urls import path
from . import views

app_name = 'hire'

urlpatterns = [
    # Admin Hire Booking URLs
    path('admin/hire/book/new/', views.AdminHireBookingView.as_view(), name='admin_hire_booking_create'),
    # Changed <uuid:pk> to <int:pk> to match the default integer primary key of HireBooking
    path('admin/hire/book/edit/<int:pk>/', views.AdminHireBookingView.as_view(), name='admin_hire_booking_edit'),

    # User multi-step booking URLs
    path('book/step1/select-datetime/', views.SelectDateTimeView.as_view(), name='step1_select_datetime'),
    path('book/step2/choose-bike/', views.BikeChoiceView.as_view(), name='step2_choose_bike'),
    path('book/step3/<int:motorcycle_id>/', views.AddonPackageView.as_view(), name='step3_addons_and_packages'),
    path('book/step4/has-account/', views.HasAccountView.as_view(), name='step4_has_account'),
    path('book/step4/no-account/', views.NoAccountView.as_view(), name='step4_no_account'),
    path('book/step5/', views.BookSumAndPaymentOptionsView.as_view(), name='step5_summary_payment_options'),
    path('book/step6/', views.PaymentDetailsView.as_view(), name='step6_payment_details'),
    path('book/step7/', views.BookingConfirmationView.as_view(), name='step7_confirmation'),
    path('book/status-check/', views.BookingStatusCheckView.as_view(), name='booking_status_check'),
]
