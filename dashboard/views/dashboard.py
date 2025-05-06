# SCOOTER_SHOP/dashboard/views/dashboard.py

# Keep necessary imports for the remaining views
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse

# Import models from the dashboard app
from dashboard.models import SiteSettings, AboutPageContent
# Import models from service app needed by the *remaining* views in this file
# ServiceBooking was moved, but ServiceType is still needed for settings views
from service.models import ServiceType # <-- Re-added this import


# Import forms from the dashboard app (Keep forms needed by remaining views)
from dashboard.forms import (
    BusinessInfoForm,
    HireBookingSettingsForm,
    ServiceBookingSettingsForm,
    VisibilitySettingsForm,
    ServiceTypeForm,
    MiscellaneousSettingsForm,
    AboutPageContentForm,
)

# Import is_staff_check from the new bookings.py file
from .bookings import is_staff_check


@user_passes_test(is_staff_check)
def dashboard_index(request):
    context = {
        'page_title': 'Admin Dashboard',
        # Add any data you want to display on the admin index here
    }
    # Updated template path
    return render(request, 'dashboard/dashboard_index.html', context)

# --- Existing Settings Views (Keep these) ---
@user_passes_test(is_staff_check)
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


@user_passes_test(is_staff_check)
def settings_hire_booking(request):
    settings = SiteSettings.get_settings()
    if request.method == 'POST':
        form = HireBookingSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hire booking settings updated successfully!')
            return redirect('dashboard:settings_hire_booking')
    else:
        form = HireBookingSettingsForm(instance=settings)
    context = {
        'page_title': 'Hire Booking Settings',
        'form': form,
        'active_tab': 'hire_booking'
    }
    return render(request, 'dashboard/settings_hire_booking.html', context)


@user_passes_test(is_staff_check)
def settings_service_booking(request):
    settings = SiteSettings.get_settings()
    if request.method == 'POST':
        form = ServiceBookingSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Service booking settings updated successfully!')
            return redirect('dashboard:settings_service_booking')
    else:
        form = ServiceBookingSettingsForm(instance=settings)
    context = {
        'page_title': 'Service Booking Settings',
        'form': form,
        'active_tab': 'service_booking'
    }
    return render(request, 'dashboard/settings_service_booking.html', context)


@user_passes_test(is_staff_check)
def settings_service_types(request):
    # Get all service types - Requires ServiceType model import
    service_types = ServiceType.objects.all().order_by('name')
    context = {
        'page_title': 'Service Types Management',
        'service_types': service_types,
        'active_tab': 'service_types'
    }
    return render(request, 'dashboard/settings_service_types.html', context)


@user_passes_test(is_staff_check)
def delete_service_type(request, pk):
    # Requires get_object_or_404, ServiceType, messages imports
    service_type = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        name = service_type.name
        service_type.delete()
        messages.success(request, f"Service type '{name}' deleted successfully!")
        return redirect('dashboard:settings_service_types')
    context = {
        'page_title': 'Delete Service Type',
        'service_type': service_type
    }
    return render(request, 'dashboard/delete_service_type.html', context)


@user_passes_test(is_staff_check)
def edit_service_type(request, pk):
    # Requires get_object_or_404, ServiceType, ServiceTypeForm, messages imports
    service_type = get_object_or_404(ServiceType, pk=pk)
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, request.FILES, instance=service_type)
        if form.is_valid():
            form.save()
            messages.success(request, f"Service type '{service_type.name}' updated successfully!")
            return redirect('dashboard:settings_service_types')
    else:
        form = ServiceTypeForm(instance=service_type)
    context = {
        'page_title': 'Edit Service Type',
        'form': form,
        'service_type': service_type,
        'active_tab': 'service_types'
    }
    return render(request, 'dashboard/add_edit_service_type.html', context)


@user_passes_test(is_staff_check)
def add_service_type(request):
    # Requires ServiceTypeForm, messages imports
    if request.method == 'POST':
        form = ServiceTypeForm(request.POST, request.FILES)
        if form.is_valid():
            service_type = form.save(commit=False)
            # Ensure estimated_duration is handled if your form logic requires it here
            service_type.save()
            messages.success(request, f"Service type '{service_type.name}' added successfully!")
            return redirect('dashboard:settings_service_types')
    else:
        form = ServiceTypeForm()
    context = {
        'page_title': 'Add New Service Type',
        'form': form,
        'active_tab': 'service_types'
    }
    return render(request, 'dashboard/add_edit_service_type.html', context)


@user_passes_test(is_staff_check)
def settings_visibility(request):
    settings = SiteSettings.get_settings()
    if request.method == 'POST':
        form = VisibilitySettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Visibility settings updated successfully!')
            return redirect('dashboard:settings_visibility')
    else:
        form = VisibilitySettingsForm(instance=settings)
    context = {
        'page_title': 'Visibility Settings',
        'form': form,
        'active_tab': 'visibility'
    }
    return render(request, 'dashboard/settings_visibility.html', context)


@user_passes_test(is_staff_check)
def settings_miscellaneous(request):
    settings = SiteSettings.get_settings()
    if request.method == 'POST':
        form = MiscellaneousSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Miscellaneous settings updated successfully!')
            return redirect('dashboard:settings_miscellaneous')
    else:
        form = MiscellaneousSettingsForm(instance=settings)
    context = {
        'page_title': 'Miscellaneous Settings',
        'form': form,
        'active_tab': 'miscellaneous'
    }
    return render(request, 'dashboard/settings_miscellaneous.html', context)


@user_passes_test(is_staff_check)
def edit_about_page(request):
    about_content, created = AboutPageContent.objects.get_or_create()
    if request.method == 'POST':
        form = AboutPageContentForm(request.POST, request.FILES, instance=about_content)
        if form.is_valid():
            form.save()
            messages.success(request, "About page content updated successfully!")
            return redirect('core:about') # Assuming 'core:about' exists
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AboutPageContentForm(instance=about_content)
    context = {
        'page_title': 'Edit About Page',
        'form': form,
        'about_content': about_content,
        'active_tab': 'about_page'
    }
    return render(request, 'dashboard/edit_about_page.html', context)