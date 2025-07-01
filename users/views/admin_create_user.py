                                   
                                                                    

from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages                                                  
from ..forms import AdminUserCreationForm                             

                                                          
def is_admin(user):
    return user.is_staff or user.is_superuser

                                     
@user_passes_test(is_admin)                                              
def admin_create_user_view(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
                                             
            messages.success(request, f'User "{user.username}" created successfully.')
                                                              
                                                                                 
            return redirect('users:admin_create_user')                                                                   
        else:
                                             
            messages.error(request, 'Error creating user. Please check the form.')
    else:
        form = AdminUserCreationForm()

    return render(request, 'users/admin_create_user.html', {'form': form})
