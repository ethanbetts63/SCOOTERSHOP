from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.conf import settings
from dashboard.models import SiteSettings
from django.contrib import messages
from core.forms.enquiry_form import EnquiryForm
from django.core.mail import send_mail


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

            send_mail(
                "Enquiry Received - Scooter Shop",
                f"Hi {enquiry.name},\n\nThank you for your enquiry. We have received your message and will get back to you shortly.\n\nYour message:\n{enquiry.message}\n\nRegards,\nScooter Shop Team",
                settings.DEFAULT_FROM_EMAIL,
                [enquiry.email],
                fail_silently=False,
            )

            send_mail(
                "New Enquiry - Scooter Shop",
                f'A new enquiry has been submitted:\n\nName: {enquiry.name}\nEmail: {enquiry.email}\nPhone: {enquiry.phone_number or "N/A"}\nMessage:\n{enquiry.message}',
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=False,
            )

            messages.success(request, "Your enquiry has been sent successfully!")
            return redirect("core:contact")
        else:
            messages.error(
                request,
                "There was an error with your submission. Please correct the errors below.",
            )
            return self.get(request, *args, **kwargs)
