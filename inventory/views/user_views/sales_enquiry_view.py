from django.shortcuts import render, redirect
from django.views import View
from inventory.forms.sales_enquiry_form import SalesEnquiryForm
from inventory.models.motorcycle import Motorcycle
from mailer.utils import send_templated_email
from django.conf import settings
from django.contrib import messages

class SalesEnquiryView(View):
    def get(self, request, motorcycle_id):
        motorcycle = Motorcycle.objects.get(id=motorcycle_id)
        form = SalesEnquiryForm(initial={'motorcycle': motorcycle})
        return render(request, 'inventory/sales_enquiry.html', {'form': form, 'motorcycle': motorcycle})

    def post(self, request, motorcycle_id):
        motorcycle = Motorcycle.objects.get(id=motorcycle_id)
        form = SalesEnquiryForm(request.POST)
        if form.is_valid():
            enquiry = form.save(commit=False)
            enquiry.motorcycle = motorcycle
            enquiry.save()

            # Send email to customer
            send_templated_email(
                recipient_list=[enquiry.email],
                subject="Enquiry Received - Scooter Shop",
                template_name="user_general_enquiry_notification.html",
                context={'enquiry': enquiry, "SITE_DOMAIN": settings.SITE_DOMAIN, "SITE_SCHEME": settings.SITE_SCHEME},
                booking=enquiry,
                profile=enquiry,
            )

            # Send email to admin
            send_templated_email(
                recipient_list=[settings.ADMIN_EMAIL],
                subject="New Enquiry - Scooter Shop",
                template_name="admin_general_enquiry_notification.html",
                context={'enquiry': enquiry, "SITE_DOMAIN": settings.SITE_DOMAIN, "SITE_SCHEME": settings.SITE_SCHEME},
                booking=enquiry,
                profile=enquiry,
            )

            messages.success(request, "Your enquiry has been sent successfully!")
            return redirect('inventory:motorcycle-detail', pk=motorcycle_id)
        return render(request, 'inventory/sales_enquiry.html', {'form': form, 'motorcycle': motorcycle})
