from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from dashboard.forms.add_package_form import AddPackageForm # Make sure this import path is correct
from hire.models.hire_packages import Package # Make sure this import path is correct

@method_decorator(login_required, name='dispatch')
class AddEditPackageView(View):
    template_name = 'dashboard/add_edit_package.html'

    def get(self, request, pk=None, *args, **kwargs):
        package = None
        if pk:
            package = get_object_or_404(Package, pk=pk)
            form = AddPackageForm(instance=package)
            title = "Edit Hire Package"
        else:
            form = AddPackageForm()
            title = "Add New Hire Package"
        context = {
            'form': form,
            'title': title,
            'package': package, # Pass package object for conditional rendering or checks
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None, *args, **kwargs):
        package = None
        if pk:
            package = get_object_or_404(Package, pk=pk)
            form = AddPackageForm(request.POST, instance=package)
        else:
            form = AddPackageForm(request.POST)

        if form.is_valid():
            package_instance = form.save()
            messages.success(request, f"Package '{package_instance.name}' saved successfully!")
            return redirect('dashboard:settings_hire_packages')
        else:
            messages.error(request, "Please correct the errors below.")
            title = "Edit Hire Package" if pk else "Add New Hire Package"
            context = {
                'form': form,
                'title': title,
                'package': package,
            }
            return render(request, self.template_name, context)