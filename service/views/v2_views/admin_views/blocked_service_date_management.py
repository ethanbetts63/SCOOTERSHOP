# SCOOTER_SHOP/dashboard/views/blocked_service_dates_management.py

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

from service.models import BlockedServiceDate
from service.forms import BlockedServiceDateForm

class BlockedServiceDateManagementView(View):
    """
    Class-based view for managing (listing and adding) blocked service dates.
    Handles both GET (display form and list) and POST (add new blocked date).
    """
    template_name = 'service/blocked_service_dates_management.html'
    form_class = BlockedServiceDateForm

    # Temporarily skipping UserPassesTestMixin as per instructions
    # def test_func(self):
    #     return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests: displays the form for adding new blocked dates
        and lists all existing blocked service dates.
        """
        form = self.form_class()
        blocked_service_dates = BlockedServiceDate.objects.all() # Fetch all blocked dates

        context = {
            'page_title': 'Blocked Service Dates Management',
            'form': form,
            'blocked_dates': blocked_service_dates,
            'active_tab': 'service_booking' # Assuming this is for navigation highlighting
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests: processes the form submission for adding a new
        blocked service date.
        """
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Blocked service date added successfully!')
            # Redirect to the same page to show the updated list and clear the form
            return redirect('dashboard:blocked_service_dates_management')
        else:
            messages.error(request, 'Error adding blocked service date. Please check the form.')
            # If form is invalid, re-render the page with errors and existing blocked dates
            blocked_service_dates = BlockedServiceDate.objects.all()
            context = {
                'page_title': 'Blocked Service Dates Management',
                'form': form,
                'blocked_dates': blocked_service_dates,
                'active_tab': 'service_booking'
            }
            return render(request, self.template_name, context)

