from django.shortcuts import render

def step3_addon_package_view(request):
    return render(request, 'hire/step3_addons_and_packages.html', {})