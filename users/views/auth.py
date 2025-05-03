# users/views/auth.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.urls import reverse # Keep this import
from django.contrib.auth import get_user_model

# The User model is now in the 'users' app, but get_user_model() finds it correctly
User = get_user_model()

# Handles user login
def login_view(request):
    if request.method == "POST":
        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            # Redirect to the page the user was trying to access, or the core index page
            # Use the namespaced URL 'core:index'
            next_url = request.GET.get('next', reverse("core:index"))
            return HttpResponseRedirect(next_url)
        else:
            return render(request, "users/login.html", { # Updated template path
                "message": "Invalid username and/or password."
            })
    else:
        # Also ensure the GET request renders the login template correctly
        return render(request, "users/login.html") # Updated template path

# Handles user logout
def logout_view(request):
    logout(request)
    # Redirect to the core index page after logout
    # Use the namespaced URL 'core:index'
    return HttpResponseRedirect(reverse("core:index"))

# Handles user registration
def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "users/register.html", { # Updated template path
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "users/register.html", { # Updated template path
                "message": "Username already taken."
            })
        login(request, user)
        # Redirect to the core index page after successful registration and login
        # Use the namespaced URL 'core:index'
        return HttpResponseRedirect(reverse("core:index"))
    else:
        return render(request, "users/register.html") # Updated template path