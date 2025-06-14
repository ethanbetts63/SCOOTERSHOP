from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from inventory.models import TempSalesBooking, SalesProfile, InventorySettings
from inventory.forms import SalesProfileForm

class Step1SalesProfileView(View):
    template_name = 'inventory/step1_sales_profile.html'

    def get(self, request, *args, **kwargs):
        temp_booking_uuid = request.session.get('temp_sales_booking_uuid')

        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            return redirect(reverse('inventory:all'))

        try:
            temp_booking = get_object_or_404(TempSalesBooking, session_uuid=temp_booking_uuid)
        except Exception as e:
            messages.error(request, f"Your booking session could not be found or is invalid. Error: {e}")
            return redirect(reverse('inventory:all'))


        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect(reverse('inventory:all'))

        sales_profile_instance = None
        if temp_booking.sales_profile:
            sales_profile_instance = temp_booking.sales_profile
        elif request.user.is_authenticated and hasattr(request.user, 'sales_profile'):
            sales_profile_instance = request.user.sales_profile
        
        sales_profile_form = SalesProfileForm(
            instance=sales_profile_instance,
            inventory_settings=inventory_settings,
            user=request.user
        )

        context = {
            'sales_profile_form': sales_profile_form,
            'temp_booking': temp_booking,
            'inventory_settings': inventory_settings,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temp_booking_uuid = request.session.get('temp_sales_booking_uuid')

        if not temp_booking_uuid:
            messages.error(request, "Your booking session has expired or is invalid. Please start again.")
            return redirect(reverse('inventory:all'))

        try:
            temp_booking = get_object_or_404(TempSalesBooking, session_uuid=temp_booking_uuid)
        except Exception as e:
            messages.error(request, f"Your booking session could not be found or is invalid. Error: {e}")
            return redirect(reverse('inventory:all'))

        inventory_settings = InventorySettings.objects.first()
        if not inventory_settings:
            messages.error(request, "Inventory settings are not configured. Please contact support.")
            return redirect(reverse('inventory:all'))

        sales_profile_instance = None
        if temp_booking.sales_profile:
            sales_profile_instance = temp_booking.sales_profile
        elif request.user.is_authenticated and hasattr(request.user, 'sales_profile'):
            sales_profile_instance = request.user.sales_profile

        sales_profile_form = SalesProfileForm(
            request.POST,
            request.FILES,
            instance=sales_profile_instance,
            inventory_settings=inventory_settings,
            user=request.user
        )

        if sales_profile_form.is_valid():
            with transaction.atomic():
                sales_profile = sales_profile_form.save(commit=False)
                if request.user.is_authenticated and not sales_profile.user:
                    sales_profile.user = request.user
                sales_profile.save()

                temp_booking.sales_profile = sales_profile
                temp_booking.save()

                messages.success(request, "Personal details saved. Proceed to booking details and appointment.")
                return redirect(reverse('inventory:step2_booking_details_and_appointment'))
        else:
            context = {
                'sales_profile_form': sales_profile_form,
                'temp_booking': temp_booking,
                'inventory_settings': inventory_settings,
            }
            messages.error(request, "Please correct the errors below.")
            return render(request, self.template_name, context)
