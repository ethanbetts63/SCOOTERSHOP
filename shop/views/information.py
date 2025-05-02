# core/views/information.py

from django.shortcuts import render, redirect
from ..models import AboutPageContent, SiteSettings # Import models


# About Page
def about(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_about_page:
        messages.error(request, "The about page is currently disabled.")
        return redirect('index') # Or a dedicated page

    about_content = AboutPageContent.objects.first()
    return render(request, "information/about.html", {"about_content": about_content})

# Contact Page
def contact(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_contact_page:
        messages.error(request, "The contact page is currently disabled.")
        return redirect('index') # Or a dedicated page
    return render(request, "information/contact.html")

# Privacy Page
def privacy(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_privacy_policy_page:
        messages.error(request, "The privacy policy page is currently disabled.")
        return redirect('index') # Or a dedicated page
    return render(request, "information/privacy.html")

# Returns Page
def returns(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_returns_page:
        messages.error(request, "The returns page is currently disabled.")
        return redirect('index') # Or a dedicated page
    return render(request, "information/returns.html")

# Security Page
def security(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_security_page:
        messages.error(request, "The security page is currently disabled.")
        return redirect('index') # Or a dedicated page
    return render(request, "information/security.html")

# Terms Page
def terms(request):
    settings = SiteSettings.get_settings()
    if not settings.enable_terms_page:
        messages.error(request, "The terms page is currently disabled.")
        return redirect('index') # Or a dedicated page
    return render(request, "information/terms.html")