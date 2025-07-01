                                                 

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test

from dashboard.models import AboutPageContent
from dashboard.forms import AboutPageContentForm

@user_passes_test(lambda u: u.is_staff)
def edit_about_page(request):
    about_content, created = AboutPageContent.objects.get_or_create()
    if request.method == 'POST':
        form = AboutPageContentForm(request.POST, request.FILES, instance=about_content)
        if form.is_valid():
            form.save()
            messages.success(request, "About page content updated successfully!")
            return redirect('core:about')                               
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