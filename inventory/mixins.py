from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = False
    login_url = 'users:login'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "You do not have sufficient privileges to access this page.")
            return redirect(f'{reverse(self.get_login_url())}?next={self.request.path}')
        else:
            return super().handle_no_permission()
