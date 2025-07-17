from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.conf import settings
from dashboard.models import SiteSettings
from django.contrib import messages
from core.forms.enquiry_form import EnquiryForm
from mailer.utils import send_templated_email


class ContactView(TemplateView):
    template_name = "core/information/contact.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site_settings = SiteSettings.get_settings()
        about_content = None

        context.update(
            {
                "settings": site_settings,
                "google_api_key": settings.GOOGLE_API_KEY,
                "form": EnquiryForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form = EnquiryForm(request.POST)
        if form.is_valid():
            enquiry = form.save()

            # Send email to customer
            send_templated_email(
                recipient_list=[enquiry.email],
                subject="Enquiry Received - Scooter Shop",
                template_name="user_general_enquiry_notification.html",
                context={
                    "enquiry": enquiry,
                    "SITE_DOMAIN": settings.SITE_DOMAIN,
                    "SITE_SCHEME": settings.SITE_SCHEME,
                },
                booking=enquiry,
                profile=enquiry,
            )

            # Send email to admin
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject="New Enquiry - Scooter Shop",
                template_name="admin_general_enquiry_notification.html",
                context={
                    "enquiry": enquiry,
                    "SITE_DOMAIN": settings.SITE_DOMAIN,
                    "SITE_SCHEME": settings.SITE_SCHEME,
                },
                booking=enquiry,
                profile=enquiry,
            )

            messages.success(request, "Your enquiry has been sent successfully!")
            return redirect("core:contact")
        else:
            messages.error(
                request,
                "There was an error with your submission. Please correct the errors below.",
            )
            context = self.get_context_data(**kwargs)
            context["form"] = form
            return self.render_to_response(context)
