# SCOOTER_SHOP/dashboard/views/settings_business_info.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from dashboard.models import SiteSettings
from dashboard.forms import BusinessInfoForm

@user_passes_test(lambda u: u.is_staff)
def settings_business_info(request):
    settings = SiteSettings.get_settings()
    if request.method == 'POST':
        form = BusinessInfoForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Business information updated successfully!')
            return redirect('dashboard:settings_business_info')
    else:
        form = BusinessInfoForm(instance=settings)
    context = {
        'page_title': 'Business Information Settings',
        'form': form,
        'active_tab': 'business_info'
    }
    return render(request, 'dashboard/settings_business_info.html', context)