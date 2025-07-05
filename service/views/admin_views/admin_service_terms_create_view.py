from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from django.contrib import messages
from service.mixins import AdminRequiredMixin  # Assuming a shared mixin
from service.forms import AdminServiceTermsForm

class ServiceTermsCreateView(AdminRequiredMixin, View):
    template_name = "service/admin_service_terms_create.html"
    form_class = AdminServiceTermsForm

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests by displaying a blank form.
        """
        form = self.form_class()
        context = {
            "form": form,
            "page_title": "Create New Service Terms Version",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests. Validates the form and saves a new ServiceTerms instance.
        The new version is automatically set to active.
        """
        form = self.form_class(request.POST)

        if form.is_valid():
            terms_version = form.save(commit=False)
            terms_version.is_active = True
            terms_version.save()
            
            messages.success(
                request, f"New Service Terms Version {terms_version.version_number} created successfully and set as active."
            )
            # Assuming the URL name for the management view is 'service_terms_management'
            return redirect(reverse("service:service_terms_management"))
        else:        
            messages.error(request, "Please correct the errors below.")
            context = {
                "form": form,
                "page_title": "Create New Service Terms Version",
            }
            return render(request, self.template_name, context)
