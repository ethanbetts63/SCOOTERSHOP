from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.urls import reverse

from payments.forms.admin_reject_refund_form import AdminRejectRefundForm
from payments.models.RefundRequest import RefundRequest
from users.views.auth import is_admin
from mailer.utils import send_templated_email

from service.models import ServiceProfile
from inventory.models import SalesProfile                                       


@method_decorator(user_passes_test(is_admin), name='dispatch')
class AdminRejectRefundView(View):

    template_name = 'payments/admin_reject_refund_form.html'

    def get(self, request, pk, *args, **kwargs):
        #--
        refund_request = get_object_or_404(RefundRequest, pk=pk)

                                                                   
        booking_reference = "N/A"
        if refund_request.service_booking:
            booking_reference = refund_request.service_booking.service_booking_reference
        elif refund_request.sales_booking:                     
            booking_reference = refund_request.sales_booking.sales_booking_reference

        form = AdminRejectRefundForm(instance=refund_request)

        context = {
            'form': form,
            'refund_request': refund_request,                   
            'title': f"Reject Refund Request for Booking {booking_reference}",
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        #--
        refund_request_instance = get_object_or_404(RefundRequest, pk=pk)
        form = AdminRejectRefundForm(request.POST, instance=refund_request_instance)

                                                                                  
        booking_reference_for_email = "N/A"
        booking_object = None
        customer_profile_object = None
        admin_management_redirect_url = 'payments:admin_refund_management'                   
        admin_edit_link_name = None                                             

        if refund_request_instance.service_booking:
            booking_reference_for_email = refund_request_instance.service_booking.service_booking_reference
            booking_object = refund_request_instance.service_booking
            customer_profile_object = refund_request_instance.service_profile
            admin_management_redirect_url = 'payments:admin_refund_management'
            admin_edit_link_name = 'payments:edit_refund_request'
        elif refund_request_instance.sales_booking:                     
            booking_reference_for_email = refund_request_instance.sales_booking.sales_booking_reference
            booking_object = refund_request_instance.sales_booking
            customer_profile_object = refund_request_instance.sales_profile
            admin_management_redirect_url = 'payments:admin_refund_management'
            admin_edit_link_name = 'payments:edit_refund_request'


        if form.is_valid():
            refund_request_instance = form.save(commit=False)
            refund_request_instance.status = 'rejected'
            refund_request_instance.processed_by = request.user
            refund_request_instance.processed_at = timezone.now()
            refund_request_instance.save()

            messages.success(request, f"Refund Request for booking '{booking_reference_for_email}' has been successfully rejected.")

                                               
            if form.cleaned_data.get('send_rejection_email'):
                recipient_email = refund_request_instance.request_email
                                                                              
                if not recipient_email:
                    if isinstance(customer_profile_object, ServiceProfile) and customer_profile_object.user:
                        recipient_email = customer_profile_object.user.email
                    elif isinstance(customer_profile_object, SalesProfile) and customer_profile_object.user:                     
                        recipient_email = customer_profile_object.user.email

                if recipient_email:
                    user_email_context = {
                        'refund_request': refund_request_instance,
                        'admin_email': settings.DEFAULT_FROM_EMAIL,
                        'booking_reference': booking_reference_for_email,
                    }
                    try:
                        send_templated_email(
                            recipient_list=[recipient_email],
                            subject=f"Update: Your Refund Request for Booking {booking_reference_for_email} Has Been Rejected",
                            template_name='user_refund_request_rejected.html',
                            context=user_email_context,
                            booking=booking_object,                              
                            service_profile=customer_profile_object if isinstance(customer_profile_object, ServiceProfile) else None,
                            sales_profile=customer_profile_object if isinstance(customer_profile_object, SalesProfile) else None,                     
                        )
                        messages.info(request, "Automated rejection email sent to the user.")
                    except Exception as e:
                        messages.warning(request, f"Failed to send user rejection email: {e}")
                else:
                    messages.warning(request, "Could not send automated rejection email to user: No recipient email found.")

                                                   
            admin_recipient_list = [settings.DEFAULT_FROM_EMAIL]
            if hasattr(settings, 'ADMINS') and settings.ADMINS:
                for name, email in settings.ADMINS:
                    if email not in admin_recipient_list:
                        admin_recipient_list.append(email)

            admin_refund_link = "#"          
            if admin_edit_link_name:
                admin_refund_link = request.build_absolute_uri(
                    reverse(admin_edit_link_name, args=[refund_request_instance.pk])
                )

            admin_email_context = {
                'refund_request': refund_request_instance,
                'admin_email': settings.DEFAULT_FROM_EMAIL,
                'admin_refund_link': admin_refund_link,
                'booking_reference': booking_reference_for_email,
            }
            try:
                send_templated_email(
                    recipient_list=admin_recipient_list,
                    subject=f"Refund Request {booking_reference_for_email} (ID: {refund_request_instance.pk}) Has Been Rejected",
                    template_name='admin_refund_request_rejected.html',
                    context=admin_email_context,
                    booking=booking_object,                              
                    service_profile=customer_profile_object if isinstance(customer_profile_object, ServiceProfile) else None,
                    sales_profile=customer_profile_object if isinstance(customer_profile_object, SalesProfile) else None,                     
                )
                messages.info(request, "Admin notification email sent regarding the rejection.")
            except Exception as e:
                messages.error(request, f"Failed to send admin rejection notification email: {e}")


            return redirect(admin_management_redirect_url)                                          
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'refund_request': refund_request_instance,                   
                'title': f"Reject Refund Request for Booking {booking_reference_for_email}",
            }
            return render(request, self.template_name, context)
