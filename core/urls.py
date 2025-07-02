from django.urls import path
from .views.admin_views import *
from .views.user_views import *

app_name = "core"

urlpatterns = [
    path("", index, name="index"),
    path("contact", ContactView.as_view(), name="contact"),
    path("privacy", PrivacyPolicyView.as_view(), name="privacy"),
    path("returns", ReturnsPolicyView.as_view(), name="returns"),
    path("security", SecurityPolicyView.as_view(), name="security"),
    path("terms", TermsOfUseView.as_view(), name="terms"),
    path(
        "dashboard/enquiries/",
        EnquiryManagementView.as_view(),
        name="enquiry_management",
    ),
    path(
        "dashboard/enquiries/<int:pk>/delete/",
        EnquiryDeleteView.as_view(),
        name="enquiry_delete",
    ),
    path(
        "dashboard/enquiries/<int:pk>/view-respond/",
        EnquiryDetailView.as_view(),
        name="enquiry_detail",
    ),
]
