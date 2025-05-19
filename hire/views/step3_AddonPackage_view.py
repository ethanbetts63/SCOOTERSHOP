# hire/views/step3_AddonPackage_view.py
from django.shortcuts import render
from django.views import View

class AddonPackageView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'hire/step3_addons_and_packages.html', {})