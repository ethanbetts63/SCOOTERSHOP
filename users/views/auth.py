                     

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.urls import reverse                   
from django.contrib.auth import get_user_model

                                                                                   
User = get_user_model()
def is_admin(user):
    return user.is_staff
                    
def login_view(request):
    if request.method == "POST":
                                 
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

                                            
        if user is not None:
            login(request, user)
                                                                                        
                                                 
            next_url = request.GET.get('next', reverse("core:index"))
            return HttpResponseRedirect(next_url)
        else:
            return render(request, "users/login.html", {                        
                "message": "Invalid username and/or password."
            })
    else:
                                                                          
        return render(request, "users/login.html")                        

                     
def logout_view(request):
    logout(request)
                                                  
                                         
    return HttpResponseRedirect(reverse("core:index"))

                           
def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

                                              
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "users/register.html", {                        
                "message": "Passwords must match."
            })

                                    
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "users/register.html", {                        
                "message": "Username already taken."
            })
        login(request, user)
                                                                                 
                                             
        return HttpResponseRedirect(reverse("core:index"))
    else:
        return render(request, "users/register.html")                        
    
    
        