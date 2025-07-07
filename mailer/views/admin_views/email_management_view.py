from django.views.generic import ListView
from mailer.models import EmailLog
from core.mixins import AdminRequiredMixin
from dashboard.models import SiteSettings


class EmailManagementView(AdminRequiredMixin, ListView):
    model = EmailLog
    template_name = "admin_email_management_view.html"
    context_object_name = "emails"
    paginate_by = 20

    def get_queryset(self):
        site_settings = SiteSettings.objects.first()
        admin_email = site_settings.admin_email if site_settings else None
        queryset = EmailLog.objects.all()
        if admin_email:
            queryset = queryset.exclude(recipient=admin_email)
        return queryset.order_by("-timestamp")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Email Management"
        return context
