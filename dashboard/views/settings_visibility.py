                                                     

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from dashboard.models import SiteSettings
from dashboard.forms import VisibilitySettingsForm

@user_passes_test(lambda u: u.is_staff)
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