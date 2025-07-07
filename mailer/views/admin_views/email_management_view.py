from django.views.generic import ListView
from mailer.models import EmailLog
from core.mixins import AdminRequiredMixin
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class EmailManagementView(AdminRequiredMixin, ListView):
    model = EmailLog
    template_name = "admin_email_management_view.html"
    context_object_name = "emails"
    paginate_by = 20

    def get_queryset(self):
        three_months_ago = timezone.now() - timedelta(days=90)
        EmailLog.objects.filter(timestamp__lt=three_months_ago).delete()
        
        admin_email = settings.ADMIN_EMAIL
        queryset = EmailLog.objects.all()
        if admin_email:
            queryset = queryset.exclude(recipient=admin_email)
        return queryset.order_by("-timestamp")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Email Management"
        return context
