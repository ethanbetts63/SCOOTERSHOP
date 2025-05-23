# SCOOTER_SHOP/dashboard/views/index.py

from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test

@user_passes_test(lambda u: u.is_staff)
def dashboard_index(request):
    """
    Main dashboard index view for staff users.
    """
    context = {
        'page_title': 'Admin Dashboard',
        # Add any data you want to display on the admin index here
    }
    return render(request, 'dashboard/dashboard_index.html', context)