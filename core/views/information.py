                           

from django.shortcuts import render, redirect
from django.conf import settings
from dashboard.models import SiteSettings, AboutPageContent 
from django.contrib.auth.decorators import user_passes_test                         

                                           
def is_staff_check(user):
    return user.is_staff

def contact(request):
    """
    Handles the Contact Us and About Us page.
    Displays content based on site settings and user staff status.
    Redirects to home if neither page is enabled and user is not staff.
    """
    site_settings = SiteSettings.get_settings()                         
    api_key = settings.GOOGLE_API_KEY
                                                                               
                                                                                           
    if not (site_settings.enable_contact_page or site_settings.enable_about_page or request.user.is_staff):
        return redirect('core:index') 

                                                                      
    about_content = None
                                                                                
    if site_settings.enable_about_page or request.user.is_staff:
        try:
                                                                       
            about_content = AboutPageContent.objects.get(pk=1)
        except AboutPageContent.DoesNotExist:
             pass 


    context = {
        'settings': site_settings,
        'about_content': about_content,
        'google_api_key': settings.GOOGLE_API_KEY,
    }

                                 
    return render(request, 'core/information/contact.html', context)

                                                               
def privacy_policy(request):
     site_settings = SiteSettings.get_settings()
     if not site_settings.enable_privacy_policy_page and not request.user.is_staff:
         return redirect('core:index')
                                          
     return render(request, 'core/information/privacy.html', {'settings': site_settings})

def returns_policy(request):
     site_settings = SiteSettings.get_settings()
     if not site_settings.enable_returns_page and not request.user.is_staff:
         return redirect('core:index')
                                          
     return render(request, 'core/information/returns.html', {'settings': site_settings})

def security_policy(request):
     site_settings = SiteSettings.get_settings()
     if not site_settings.enable_security_page and not request.user.is_staff:
         return redirect('core:index')
                                           
     return render(request, 'core/information/security.html', {'settings': site_settings})

def terms_of_use(request):
     site_settings = SiteSettings.get_settings()
     if not site_settings.enable_terms_page and not request.user.is_staff:
         return redirect('core:index')
                                        
     return render(request, 'core/information/terms.html', {'settings': site_settings})

