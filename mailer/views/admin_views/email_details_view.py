from django.views.generic import DetailView
from mailer.models import EmailLog
from core.mixins import AdminRequiredMixin
from django.template import Context, Template
from django.shortcuts import render

class EmailDetailView(AdminRequiredMixin, DetailView):
    model = EmailLog
    template_name = "admin_email_details_view.html"
    context_object_name = "email"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Email Details"
        email_log = self.get_object()
        if email_log.template_name and email_log.context:
            try:
                template = Template(open(f'mailer/templates/{email_log.template_name}').read())
                rendered_email = template.render(Context(email_log.context))
                context['rendered_email'] = rendered_email
            except Exception as e:
                context['rendered_email'] = f"<p>Error rendering email: {e}</p>"
        return context
