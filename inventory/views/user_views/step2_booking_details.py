from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.contrib import messages

from inventory.models import TempSalesBooking, InventorySettings, SalesBooking, SalesProfile
from inventory.forms.sales_booking_appointment_form import BookingAppointmentForm

class Step2BookingDetailsView(View):
    template_name = 'inventory/step2_booking_details.html'

    def get(self, request, *args, **kwargs):
        temp_booking_id = request.session.get('current_temp_booking_id')
        if not temp_booking_id:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            return redirect(reverse('core:index'))

        temp_booking = get_object_or_404(TempSalesBooking, pk=temp_booking_id)

        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect(reverse('core:index'))

        initial_data = {
            'request_viewing': temp_booking.request_viewing,
            'appointment_date': temp_booking.appointment_date,
            'appointment_time': temp_booking.appointment_time,
            'customer_notes': temp_booking.customer_notes,
        }

        form = BookingAppointmentForm(
            initial=initial_data,
            deposit_required_for_flow=temp_booking.deposit_required_for_flow,
            inventory_settings=inventory_settings
        )

        context = {
            'form': form,
            'temp_booking': temp_booking,
            'inventory_settings': inventory_settings,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temp_booking_id = request.session.get('current_temp_booking_id')
        if not temp_booking_id:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            return redirect(reverse('core:index'))

        temp_booking = get_object_or_404(TempSalesBooking, pk=temp_booking_id)

        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect(reverse('core:index'))

        form = BookingAppointmentForm(
            request.POST,
            deposit_required_for_flow=temp_booking.deposit_required_for_flow,
            inventory_settings=inventory_settings
        )

        if form.is_valid():
            with transaction.atomic():
                customer_notes = form.cleaned_data.get('customer_notes')
                request_viewing = form.cleaned_data.get('request_viewing')
                appointment_date = form.cleaned_data.get('appointment_date')
                appointment_time = form.cleaned_data.get('appointment_time')

                temp_booking.customer_notes = customer_notes
                temp_booking.request_viewing = request_viewing
                temp_booking.appointment_date = appointment_date
                temp_booking.appointment_time = appointment_time
                temp_booking.save()

                if temp_booking.deposit_required_for_flow:
                    messages.success(request, "Booking details saved. Proceed to payment.")
                    return redirect(reverse('inventory:step3_payment'))
                else:
                    sales_booking_status = 'enquired'
                    if request_viewing:
                        sales_booking_status = 'pending_confirmation'

                    SalesBooking.objects.create(
                        motorcycle=temp_booking.motorcycle,
                        sales_profile=temp_booking.sales_profile,
                        customer_notes=customer_notes,
                        request_viewing=request_viewing,
                        appointment_date=appointment_date,
                        appointment_time=appointment_time,
                        booking_status=sales_booking_status,
                        currency=inventory_settings.currency_code
                    )
                    temp_booking.delete()
                    messages.success(request, "Your enquiry has been submitted. We will get back to you shortly!")
                    return redirect(reverse('inventory:confirmation_page'))
        else:
            context = {
                'form': form,
                'temp_booking': temp_booking,
                'inventory_settings': inventory_settings,
            }
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, context)
