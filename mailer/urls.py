from django.urls import path
from .views.admin_views import EmailManagementView, EmailDetailView, TestEmailView

app_name = "mailer"

urlpatterns = [
    path(
        "dashboard/emails/",
        EmailManagementView.as_view(),
        name="email_management",
    ),
    path(
        "dashboard/emails/<int:pk>/",
        EmailDetailView.as_view(),
        name="email_detail",
    ),
    path(
        "dashboard/emails/test/",
        TestEmailView.as_view(),
        name="test_emails",
    ),
]
