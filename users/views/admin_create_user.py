# SCOOTER_SHOP/users/views/admin.py
# Create a new file named admin.py inside your users/views directory

from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages # Optional: for displaying success/error messages
from ..forms import AdminUserCreationForm # Import the form we created

# Helper function to check if a user is staff or superuser
def is_admin(user):
    return user.is_staff or user.is_superuser

# View for admin to create a new user
@user_passes_test(is_admin) # Decorator to restrict access to admin users
def admin_create_user_view(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Optional: Add a success message
            messages.success(request, f'User "{user.username}" created successfully.')
            # Redirect to a success page or another admin page
            # You might want to redirect to a list of users or a user detail page
            return redirect('users:admin_create_user') # Redirect back to the create page for another user or change this
        else:
             # Optional: Add an error message
            messages.error(request, 'Error creating user. Please check the form.')
    else:
        form = AdminUserCreationForm()

    return render(request, 'users/admin_create_user.html', {'form': form})
