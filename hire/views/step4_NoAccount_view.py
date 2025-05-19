# hire/views/step4_NoAccount_view.py
from django.shortcuts import render
from django.views import View

class NoAccountView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'hire/step4_no_account.html', {})