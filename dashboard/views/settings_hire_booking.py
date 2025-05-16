# SCOOTER_SHOP/dashboard/views/settings_hire_booking.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from dashboard.models import HireSettings
from dashboard.forms import HireBookingSettingsForm

@user_passes_test(lambda u: u.is_staff)
def settings_hire_booking(request):
    settings, created = HireSettings.objects.get_or_create()

    if created:
        messages.info(request, "Initial Hire Settings object created with default values.")

    if request.method == 'POST':
        form = HireBookingSettingsForm(request.POST, instance=settings)
        print("Is form valid?", form.is_valid())
        if form.is_valid():
            form.save()
            messages.success(request, 'Hire booking settings updated successfully!')
            return redirect('dashboard:settings_hire_booking')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = HireBookingSettingsForm(instance=settings)

    context = {
        'page_title': 'Hire Booking Settings',
        'form': form,
        'active_tab': 'hire_booking'
    }
    return render(request, 'dashboard/settings_hire_booking.html', context)