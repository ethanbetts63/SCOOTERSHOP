# SCOOTER_SHOP/dashboard/views/settings_service_booking.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from dashboard.models import SiteSettings
from service.forms import ServiceSettingsForm

@user_passes_test(lambda u: u.is_staff)
def settings_service_booking(request):
    settings = SiteSettings.get_settings()
    form = ServiceSettingsForm(instance=settings)

    if request.method == 'POST':
        if 'service_settings_submit' in request.POST:
            form = ServiceSettingsForm(request.POST, instance=settings)
            if form.is_valid():
                form.save()
                messages.success(request, 'Service booking settings updated successfully!')
                return redirect('dashboard:settings_service_booking')
            else:
                messages.error(request, 'Error updating service booking settings. Please check the form.')

    context = {
        'page_title': 'Service Booking Settings',
        'form': form,
        'active_tab': 'service_booking'
    }
    return render(request, 'dashboard/settings_service_booking.html', context)