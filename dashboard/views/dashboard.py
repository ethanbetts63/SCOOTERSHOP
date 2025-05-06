from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test # Import the decorator
from django.urls import reverse # Import reverse for redirects

# Import models from the dashboard app
from dashboard.models import SiteSettings, AboutPageContent
from service.models import ServiceType

# Import forms from the dashboard app
from dashboard.forms import (
    BusinessInfoForm,
    HireBookingSettingsForm,
    ServiceBookingSettingsForm,
    VisibilitySettingsForm,
    ServiceTypeForm,
    MiscellaneousSettingsForm,
    AboutPageContentForm,
)

# Helper function to check if a user is staff
def is_staff_check(user):
    return user.is_staff

@user_passes_test(is_staff_check)
def dashboard_index(request):
    context = {
        'page_title': 'Admin Dashboard',
        # Add any data you want to display on the admin index here
    }
    # Updated template path
    return render(request, 'dashboard/dashboard_index.html', context)

# --- New View for Bookings ---
@user_passes_test(is_staff_check)
def service_bookings_view(request):
    """
    View for the service bookings page in the admin dashboard.
    Requires staff user.
    """
    context = {
        'page_title': 'Manage Service Bookings',
        # Add any data related to bookings here in the future
    }
    # Render the bookings.html template
    return render(request, 'dashboard/service_bookings.html', context)

# --- Existing Settings Views ---
@user_passes_test(is_staff_check)
def settings_business_info(request):
    # Get the singleton SiteSettings instance
    settings = SiteSettings.get_settings()

    if request.method == 'POST':
        form = BusinessInfoForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Business information updated successfully!')
            # Updated redirect URL to use dashboard namespace
            return redirect('dashboard:settings_business_info')
    else:
        form = BusinessInfoForm(instance=settings)

    context = {
        'page_title': 'Business Information Settings',
        'form': form,
        'active_tab': 'business_info'
    }
    # Updated template path
    return render(request, 'dashboard/settings_business_info.html', context)

@user_passes_test(is_staff_check)
def settings_hire_booking(request):
    # Get the singleton SiteSettings instance
    settings = SiteSettings.get_settings()

    if request.method == 'POST':
        form = HireBookingSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hire booking settings updated successfully!')
            # Updated redirect URL to use dashboard namespace
            return redirect('dashboard:settings_hire_booking')
    else:
        form = HireBookingSettingsForm(instance=settings)

    context = {
        'page_title': 'Hire Booking Settings',
        'form': form,
        'active_tab': 'hire_booking'
    }
    # Updated template path
    return render(request, 'dashboard/settings_hire_booking.html', context)

@user_passes_test(is_staff_check)
def settings_service_booking(request):
    # Get the singleton SiteSettings instance
    settings = SiteSettings.get_settings()

    if request.method == 'POST':
        form = ServiceBookingSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service booking settings updated successfully!')
            # Updated redirect URL to use dashboard namespace
            return redirect('dashboard:settings_service_booking')
    else:
        form = ServiceBookingSettingsForm(instance=settings)

    context = {
        'page_title': 'Service Booking Settings',
        'form': form,
        'active_tab': 'service_booking'
    }
    # Updated template path
    return render(request, 'dashboard/settings_service_booking.html', context)

@user_passes_test(is_staff_check)
def settings_service_types(request):
    # Get all service types
    service_types = ServiceType.objects.all().order_by('name')

    context = {
        'page_title': 'Service Types Management',
        'service_types': service_types,
        'active_tab': 'service_types' # Assuming you use active_tab for highlighting navigation
    }
    # Updated template path
    return render(request, 'dashboard/settings_service_types.html', context)

@user_passes_test(is_staff_check)
def delete_service_type(request, pk):
    service_type = get_object_or_404(ServiceType, pk=pk)

    if request.method == 'POST':
        name = service_type.name
        service_type.delete()
        messages.success(request, f"Service type '{name}' deleted successfully!")
        # Updated redirect URL to use dashboard namespace
        return redirect('dashboard:settings_service_types')

    context = {
        'page_title': 'Delete Service Type',
        'service_type': service_type
    }
    # Updated template path
    return render(request, 'dashboard/delete_service_type.html', context)

@user_passes_test(is_staff_check)
def edit_service_type(request, pk):
    # View for editing an existing service type on a separate page
    service_type = get_object_or_404(ServiceType, pk=pk)

    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, request.FILES, instance=service_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Service type '{service_type.name}' updated successfully!")
            # Updated redirect URL to use dashboard namespace
            return redirect('dashboard:settings_service_types') # Redirect to the list view
    else:
        form = ServiceTypeForm(instance=service_type)

    context = {
        'page_title': 'Edit Service Type',
        'form': form,
        'service_type': service_type, # Pass the service_type object to the template for the button text logic
        'active_tab': 'service_types' # Assuming you use active_tab for highlighting navigation
    }
    # Updated template path
    return render(request, 'dashboard/add_edit_service_type.html', context)

@user_passes_test(is_staff_check)
def add_service_type(request):
    # View for adding a new service type on a separate page
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the form without committing to get the instance
            service_type = form.save(commit=False)

            # Manually set the estimated_duration from the cleaned_data
            # This value was calculated in the form's clean method
            service_type.estimated_duration = form.cleaned_data['estimated_duration']

            # Now save the instance to the database
            service_type.save()

            messages.success(request, f"Service type '{service_type.name}' added successfully!")
            # Updated redirect URL to use dashboard namespace
            return redirect('dashboard:settings_service_types') # Redirect to the list view
    else:
        form = ServiceTypeForm()

    context = {
        'page_title': 'Add New Service Type',
        'form': form,
        'active_tab': 'service_types' # Assuming you use active_tab for highlighting navigation
    }
    # Updated template path
    return render(request, 'dashboard/add_edit_service_type.html', context)

@user_passes_test(is_staff_check)
def settings_visibility(request):
    # Get the singleton SiteSettings instance
    settings = SiteSettings.get_settings() # Use get_settings static method

    if request.method == 'POST':
        form = VisibilitySettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Visibility settings updated successfully!')
            # Updated redirect URL to use dashboard namespace
            return redirect('dashboard:settings_visibility')
    else:
        form = VisibilitySettingsForm(instance=settings)

    context = {
        'page_title': 'Visibility Settings',
        'form': form,
        'active_tab': 'visibility'
    }
    # Updated template path
    return render(request, 'dashboard/settings_visibility.html', context)

@user_passes_test(is_staff_check)
def settings_miscellaneous(request):
    # Get the singleton SiteSettings instance
    settings = SiteSettings.get_settings()

    if request.method == 'POST':
        form = MiscellaneousSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Miscellaneous settings updated successfully!')
            # Updated redirect URL to use dashboard namespace
            return redirect('dashboard:settings_miscellaneous')
    else:
        form = MiscellaneousSettingsForm(instance=settings)

    context = {
        'page_title': 'Miscellaneous Settings',
        'form': form,
        'active_tab': 'miscellaneous'
    }
    # Updated template path
    return render(request, 'dashboard/settings_miscellaneous.html', context)

@user_passes_test(is_staff_check)
def edit_about_page(request):
    # Get or create the about page content
    about_content, created = AboutPageContent.objects.get_or_create()

    if request.method == 'POST':
        form = AboutPageContentForm(request.POST, request.FILES, instance=about_content)
        if form.is_valid():
            form.save()
            messages.success(request, "About page content updated successfully!")
            # Redirect back to the edit page or another relevant page
            # Updated redirect URL - assuming 'about' will be namespaced under 'core'
            return redirect('core:about') # Redirect to the public about page
        else:
            messages.error(request, "Please correct the errors below.")
            # For debugging
            print(f"Form errors: {form.errors}")
    else:
        form = AboutPageContentForm(instance=about_content)

    context = {
        'page_title': 'Edit About Page',
        'form': form,
        'about_content': about_content, # Pass the object for potential display
        'active_tab': 'about_page' # Assuming an active tab for this
    }
    # Updated template path
    return render(request, 'dashboard/edit_about_page.html', context)
