from django.views.generic import DetailView
from mailer.models import EmailLog
from core.mixins import AdminRequiredMixin
import base64

class EmailDetailView(AdminRequiredMixin, DetailView):
    model = EmailLog
    template_name = "admin_email_details_view.html"
    context_object_name = "email"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Email Details"
        email_log = self.get_object()
        
        # Encode the HTML content in base64 to use in a data URL
        if email_log.html_content:
            encoded_html = base64.b64encode(email_log.html_content.encode('utf-8')).decode('utf-8')
            context['encoded_html_content'] = encoded_html
        else:
            context['encoded_html_content'] = base64.b64encode(b'<p>No content available.</p>').decode('utf-8')
            
        return context
