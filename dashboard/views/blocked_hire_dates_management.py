                                                               

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from dashboard.models import BlockedHireDate
from dashboard.forms import BlockedHireDateForm

@user_passes_test(lambda u: u.is_staff)
def blocked_hire_dates_management(request):
    blocked_hire_dates = BlockedHireDate.objects.all()

    if request.method == 'POST':
        form = BlockedHireDateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Blocked hire date added successfully!')
            return redirect('dashboard:blocked_hire_dates_management')
        else:
            messages.error(request, 'Error adding blocked hire date. Please check the form.')
    else:
        form = BlockedHireDateForm()

    context = {
        'page_title': 'Blocked Hire Dates Management',
        'form': form,
        'blocked_dates': blocked_hire_dates,
        'active_tab': 'hire_booking'
    }
    return render(request, 'dashboard/blocked_hire_dates.html', context)