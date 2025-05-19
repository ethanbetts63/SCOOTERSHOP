from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from dashboard.forms.add_package_form import AddPackageForm
from hire.models.hire_packages import Package

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
            'package': package,
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
            # Save the main Package instance first.
            # For new instances, ManyToMany data can't be saved until the instance has an ID.
            # Using commit=False prevents Django from saving M2M data until save_m2m() is called.
            package_instance = form.save(commit=False)
            package_instance.save() # This saves the Package object and gives it an ID.

            # Now, save the ManyToMany data. This method requires the instance to be saved.
            form.save_m2m()

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