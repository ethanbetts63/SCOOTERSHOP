from django.urls import path
from . import views

app_name = 'hire'

urlpatterns = [
    path('book/step3/', views.step3_addon_package_view, name='step3_addons_packages'),
    path('book/step4/has-account/', views.step4_has_account_view, name='step4_has_account'),
    path('book/step4/no-account/', views.step4_no_account_view, name='step4_no_account'),
    path('book/step5/', views.step5_book_sum_and_payment_options_view, name='step5_summary_payment_options'),
    path('book/step6/', views.step6_payment_details_view, name='step6_payment_details'),
    path('book/step7/', views.step7_booking_confirmation_view, name='step7_confirmation'),
]