# # inventory/tests/admin_views/test_blocked_sales_date_views.py

# import datetime
# from django.test import TestCase, Client
# from django.urls import reverse
# from django.contrib.auth import get_user_model
# from django.contrib.messages import get_messages

# from inventory.models import BlockedSalesDate
# from ...test_helpers.model_factories import UserFactory, BlockedSalesDateFactory

# User = get_user_model()

# class BlockedSalesDateManagementViewTest(TestCase):
#     """
#     Tests for the BlockedSalesDateManagementView.
#     """

#     @classmethod
#     def setUpTestData(cls):
#         """
#         Set up non-modified objects used by all test methods.
#         """
#         cls.client = Client()
#         cls.url = reverse('inventory:blocked_sales_date_management')

#         # Create a regular user (non-admin)
#         cls.user = UserFactory(username='testuser', is_staff=False, is_superuser=False)
#         cls.user.set_password('password123')
#         cls.user.save()

#         # Create an admin user
#         cls.admin_user = UserFactory(username='adminuser', is_staff=True, is_superuser=True)
#         cls.admin_user.set_password('adminpass123')
#         cls.admin_user.save()

#         # Create several blocked dates to test ordering
#         dates = [
#             datetime.date(2025, 7, 15),
#             datetime.date(2025, 6, 1),
#             datetime.date(2025, 8, 20),
#         ]
#         for date in dates:
#             BlockedSalesDateFactory(start_date=date, end_date=date + datetime.timedelta(days=1))

#     def test_view_redirects_for_anonymous_user(self):
#         """
#         Test that an unauthenticated user is redirected to the login page.
#         """
#         response = self.client.get(self.url)
#         self.assertRedirects(response, f'{reverse("users:login")}?next={self.url}')

#     def test_view_redirects_for_non_admin_user(self):
#         """
#         Test that a non-admin user is redirected to the login page.
#         """
#         self.client.login(username='testuser', password='password123')
#         response = self.client.get(self.url)
#         # An AdminRequiredMixin usually redirects to login for non-staff users
#         self.assertRedirects(response, f'{reverse("users:login")}?next={self.url}')

#     def test_view_accessible_for_admin_user(self):
#         """
#         Test that an admin user can access the management page.
#         """
#         self.client.login(username='adminuser', password='adminpass123')
#         response = self.client.get(self.url)
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'inventory/admin_blocked_sales_date_management.html')

#     def test_queryset_ordering(self):
#         """
#         Test that the blocked dates are ordered by start_date.
#         """
#         self.client.login(username='adminuser', password='adminpass123')
#         response = self.client.get(self.url)
        
#         self.assertEqual(response.status_code, 200)
#         context_dates = list(response.context['blocked_sales_dates'])
        
#         # Check if the list of dates from the context is sorted
#         sorted_dates = sorted(context_dates, key=lambda x: x.start_date)
#         self.assertEqual(context_dates, sorted_dates, "Dates are not correctly ordered by start_date.")

#     def test_context_data(self):
#         """
#         Test that the correct context data is passed to the template.
#         """
#         self.client.login(username='adminuser', password='adminpass123')
#         response = self.client.get(self.url)

#         self.assertIn('blocked_sales_dates', response.context)
#         self.assertIn('page_title', response.context)
#         self.assertEqual(response.context['page_title'], "Blocked Sales Dates Management")
