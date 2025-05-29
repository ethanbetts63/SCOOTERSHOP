# dashboard/views/add_edit_driver_profile_view.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from dashboard.forms.driver_profile_form import DriverProfileForm # Import the new form
from hire.models.driver_profile import DriverProfile # Import the DriverProfile model
from users.models import User # Import the User model to pass to context if needed

@method_decorator(login_required, name='dispatch')
class AddEditDriverProfileView(View):
    """
    View for adding and editing DriverProfile instances.
    """
    template_name = 'dashboard/add_edit_driver_profile.html'

    def get(self, request, pk=None, *args, **kwargs):
        driver_profile = None
        if pk:
            driver_profile = get_object_or_404(DriverProfile, pk=pk)
            form = DriverProfileForm(instance=driver_profile)
            title = "Edit Driver Profile"
        else:
            # When adding a new profile, ensure the 'user' field is blank by default
            form = DriverProfileForm(initial={'user': None})
            title = "Add New Driver Profile"

        context = {
            'form': form,
            'title': title,
            'driver_profile': driver_profile, # Pass the instance for conditional rendering in template
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        driver_profile = None
        if pk:
            driver_profile = get_object_or_404(DriverProfile, pk=pk)
            # When handling file uploads, request.FILES must be passed to the form
            form = DriverProfileForm(request.POST, request.FILES, instance=driver_profile)
        else:
            # When handling file uploads, request.FILES must be passed to the form
            form = DriverProfileForm(request.POST, request.FILES)

        if form.is_valid():
            driver_profile_instance = form.save() # Save the form, including file uploads
            messages.success(request, f"Driver Profile for '{driver_profile_instance.name}' saved successfully!")
            return redirect('dashboard:settings_driver_profiles')
        else:
            messages.error(request, "Please correct the errors below.")
            title = "Edit Driver Profile" if pk else "Add New Driver Profile"
            context = {
                'form': form,
                'title': title,
                'driver_profile': driver_profile,
            }
            return render(request, self.template_name, context)

