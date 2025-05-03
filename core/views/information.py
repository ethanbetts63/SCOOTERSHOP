# core/views/information.py

from django.shortcuts import render, redirect
from django.contrib import messages # Import messages

# Import models remaining in the core app
from dashboard.models import AboutPageContent, SiteSettings # Assuming these remain in core app


# About Page
def about(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_about_page: # Assuming this setting exists
        messages.error(request, "The about page is currently disabled.")
        # Updated redirect URL to use the core namespace
        return redirect('core:index')

    # Get the about page content (first object, assuming a singleton or order)
    try:
        about_content = AboutPageContent.objects.first()
    except Exception as e:
        print(f"Error fetching about page content: {e}")
        about_content = None
        messages.warning(request, "Could not load about page content.")

    context = {"about_content": about_content}
    # Updated template path
    return render(request, "core/information/about.html", context)

# Contact Page
def contact(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_contact_page: # Assuming this setting exists
        messages.error(request, "The contact page is currently disabled.")
        # Updated redirect URL to use the core namespace
        return redirect('core:index')
    # Updated template path
    return render(request, "core/information/contact.html")

# Privacy Page
def privacy(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_privacy_policy_page: # Assuming this setting exists
        messages.error(request, "The privacy policy page is currently disabled.")
        # Updated redirect URL to use the core namespace
        return redirect('core:index')
    # Updated template path
    return render(request, "core/information/privacy.html")

# Returns Page
def returns(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_returns_page: # Assuming this setting exists
        messages.error(request, "The returns page is currently disabled.")
        # Updated redirect URL to use the core namespace
        return redirect('core:index')
    # Updated template path
    return render(request, "core/information/returns.html")

# Security Page
def security(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_security_page: # Assuming this setting exists
        messages.error(request, "The security page is currently disabled.")
        # Updated redirect URL to use the core namespace
        return redirect('core:index')
    # Updated template path
    return render(request, "core/information/security.html")

# Terms Page
def terms(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_terms_page: # Assuming this setting exists
        messages.error(request, "The terms page is currently disabled.")
        # Updated redirect URL to use the core namespace
        return redirect('core:index')
    # Updated template path
    return render(request, "core/information/terms.html")