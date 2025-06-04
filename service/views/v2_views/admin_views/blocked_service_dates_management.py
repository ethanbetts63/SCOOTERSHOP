# SCOOTER_SHOP/dashboard/views/blocked_service_dates_management.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from service.models import BlockedServiceDate
from service.forms import BlockedServiceDateForm

@user_passes_test(lambda u: u.is_staff)
def blocked_service_dates_management(request):
    blocked_service_dates = BlockedServiceDate.objects.all()

    if request.method == 'POST':
        form = BlockedServiceDateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Blocked service date added successfully!')
            return redirect('dashboard:blocked_service_dates_management')
        else:
            messages.error(request, 'Error adding blocked service date. Please check the form.')
    else:
        form = BlockedServiceDateForm()

    context = {
        'page_title': 'Blocked Service Dates Management',
        'form': form,
        'blocked_dates': blocked_service_dates,
        'active_tab': 'service_booking'
    }
    return render(request, 'dashboard/blocked_service_dates.html', context)