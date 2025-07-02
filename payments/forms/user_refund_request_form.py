from django import forms
from django.utils.translation import gettext_lazy as _
import re
from service.models import ServiceBooking, ServiceProfile
from inventory.models import SalesBooking, SalesProfile
from payments.models.RefundRequest import RefundRequest


class RefundRequestForm(forms.ModelForm):
    booking_reference = forms.CharField(
        max_length=50,
        label=_("Booking Reference"),
        help_text=_("Enter your unique booking reference number (e.g., SERVICE-XXXXX, or SBK-XXXXX).")
    )
    email = forms.EmailField(
        label=_("Your Email Address"),
        help_text=_("Enter the email address used for this booking.")
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': _('Optional: Briefly explain why you are requesting a refund.')}),
        required=False,
        label=_("Reason for Refund")
    )

    class Meta:
        model = RefundRequest
        fields = ['booking_reference', 'email', 'reason']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        booking_reference = cleaned_data.get('booking_reference')
        email = cleaned_data.get('email')
        reason = cleaned_data.get('reason')

        booking_object = None
        customer_profile = None
        payment_object = None
        booking_type = None

        if booking_reference and email:
            try:

                if not booking_object and re.match(r'^(SERVICE|SVC)-\w+', booking_reference, re.IGNORECASE):
                    try:
                        booking_object = ServiceBooking.objects.get(service_booking_reference__iexact=booking_reference)
                        customer_profile = booking_object.service_profile
                        payment_object = booking_object.payment
                        booking_type = 'service'
                    except ServiceBooking.DoesNotExist:
                        pass
                
                if not booking_object and re.match(r'^SBK-\w+', booking_reference, re.IGNORECASE):
                    try:
                        booking_object = SalesBooking.objects.get(sales_booking_reference__iexact=booking_reference)
                        customer_profile = booking_object.sales_profile
                        payment_object = booking_object.payment
                        booking_type = 'sales'
                    except SalesBooking.DoesNotExist:
                        pass

                if not booking_object:
                    self.add_error('booking_reference', _("No booking found with this reference number."))
                    return cleaned_data

                if not customer_profile or customer_profile.email.lower() != email.lower():
                    self.add_error('email', _("The email address does not match the one registered for this booking."))
                    return cleaned_data

                if not payment_object:
                    self.add_error('booking_reference', _("No payment record found for this booking."))
                    return cleaned_data

                if payment_object.status != 'succeeded':
                    self.add_error('booking_reference', _("This booking's payment is not in a 'succeeded' status and is not eligible for a refund."))
                    return cleaned_data

                existing_refund_requests = RefundRequest.objects.filter(
                    payment=payment_object,
                    status__in=['unverified', 'pending', 'approved', 'reviewed_pending_approval']
                )
                if existing_refund_requests.exists():
                    self.add_error(None, _("A refund request for this booking is already in progress."))
                    return cleaned_data

                self.instance.payment = payment_object
                self.instance.status = 'unverified'
                self.instance.is_admin_initiated = False
                self.instance.reason = reason
                self.instance.request_email = email.lower()

                self.instance.service_booking = None
                self.instance.service_profile = None
                self.instance.sales_booking = None
                self.instance.sales_profile = None

                if booking_type == 'service':
                    self.instance.service_booking = booking_object
                    self.instance.service_profile = customer_profile
                elif booking_type == 'sales':
                    self.instance.sales_booking = booking_object
                    self.instance.sales_profile = customer_profile

            except ServiceProfile.DoesNotExist:
                self.add_error(None, _("Associated service profile not found for this service booking."))
            except SalesProfile.DoesNotExist:
                self.add_error(None, _("Associated sales profile not found for this sales booking."))
            except Exception as e:
                self.add_error(None, _(f"An unexpected error occurred: {e}. Please try again or contact support."))
        else:
            pass

        return cleaned_data

    def save(self, commit=True):
        refund_request = super().save(commit=False)
        if commit:
            refund_request.save()
        return refund_request