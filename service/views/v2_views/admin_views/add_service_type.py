# # SCOOTER_SHOP/dashboard/views/add_service_type.py

# from django.shortcuts import render, redirect
# from django.contrib import messages
# from django.contrib.auth.decorators import user_passes_test

# from service.forms import ServiceTypeForm

# @user_passes_test(lambda u: u.is_staff)
# def add_service_type(request):
#     if request.method == 'POST':
#         form = ServiceTypeForm(request.POST, request.FILES)
#         if form.is_valid():
#             service_type = form.save(commit=False)
#             service_type.estimated_duration = form.cleaned_data['estimated_duration']
#             service_type.save()
#             messages.success(request, f"Service type '{service_type.name}' added successfully!")
#             return redirect('dashboard:settings_service_types')
#     else:
#         form = ServiceTypeForm()
#     context = {
#         'page_title': 'Add New Service Type',
#         'form': form,
#         'active_tab': 'service_types'
#     }
#     return render(request, 'dashboard/add_edit_service_type.html', context)