# core/views/information.py

from django.shortcuts import render, redirect
from django.conf import settings
from dashboard.models import SiteSettings, AboutPageContent # Assuming models are in core.models
from django.contrib.auth.decorators import user_passes_test # Import for staff check

# Helper function to check if user is staff
def is_staff_check(user):
    return user.is_staff

def contact(request):
    """
    Handles the Contact Us and About Us page.
    Displays content based on site settings and user staff status.
    Redirects to home if neither page is enabled and user is not staff.
    """
    site_settings = SiteSettings.get_settings() # Get your site settings

    # Check if the page should be accessible based on settings and staff status
    # The page is accessible if contact is enabled OR about is enabled OR the user is staff
    if not (site_settings.enable_contact_page or site_settings.enable_about_page or request.user.is_staff):
        return redirect('core:index') 

    # Fetch AboutPageContent if about page is enabled or user is staff
    about_content = None
    # Only attempt to fetch if the About section should potentially be displayed
    if site_settings.enable_about_page or request.user.is_staff:
        try:
            # Assuming AboutPageContent has a single instance with pk=1
            about_content = AboutPageContent.objects.get(pk=1)
        except AboutPageContent.DoesNotExist:
             pass 


    context = {
        'settings': site_settings,
        'about_content': about_content,
    }

    # Render the contact template
    return render(request, 'core/information/contact.html', context)

# Existing information views (ensure these match what you have)
def privacy_policy(request):
     site_settings = SiteSettings.get_settings()
     if not site_settings.enable_privacy_policy_page and not request.user.is_staff:
         return redirect('core:index')
     # Render your privacy policy template
     return render(request, 'core/information/privacy.html', {'settings': site_settings})

def returns_policy(request):
     site_settings = SiteSettings.get_settings()
     if not site_settings.enable_returns_page and not request.user.is_staff:
         return redirect('core:index')
     # Render your returns policy template
     return render(request, 'core/information/returns.html', {'settings': site_settings})

def security_policy(request):
     site_settings = SiteSettings.get_settings()
     if not site_settings.enable_security_page and not request.user.is_staff:
         return redirect('core:index')
     # Render your security policy template
     return render(request, 'core/information/security.html', {'settings': site_settings})

def terms_of_use(request):
     site_settings = SiteSettings.get_settings()
     if not site_settings.enable_terms_page and not request.user.is_staff:
         return redirect('core:index')
     # Render your terms of use template
     return render(request, 'core/information/terms.html', {'settings': site_settings})

