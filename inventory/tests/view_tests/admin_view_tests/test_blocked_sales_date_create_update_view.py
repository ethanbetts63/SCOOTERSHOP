# import datetime
# from django.test import TestCase, Client
# from django.urls import reverse
# from django.contrib.auth import get_user_model
# from django.contrib.messages import get_messages

# from inventory.models import BlockedSalesDate
# from ...test_helpers.model_factories import UserFactory, BlockedSalesDateFactory

# User = get_user_model()

# class BlockedSalesDateCreateUpdateViewTest(TestCase):
    
#     @classmethod
#     def setUpTestData(cls):
#         cls.client = Client()
        
        
#         cls.user = UserFactory(username='testuser', is_staff=False, is_superuser=False)
#         cls.user.set_password('password123')
#         cls.user.save()

        
#         cls.admin_user = UserFactory(username='adminuser', is_staff=True, is_superuser=True)
#         cls.admin_user.set_password('adminpass123')
#         cls.admin_user.save()

        
#         cls.blocked_date = BlockedSalesDateFactory(
#             start_date=datetime.date(2025, 12, 24),
#             end_date=datetime.date(2025, 12, 26),
#             description="Christmas Break"
#         )
        
        
#         cls.create_url = reverse('inventory:blocked_sales_date_create_update')
#         cls.update_url = reverse('inventory:blocked_sales_date_create_update', kwargs={'pk': cls.blocked_date.pk})
#         cls.management_url = reverse('inventory:blocked_sales_date_management')
        
        
#         cls.non_existent_pk = 9999
#         cls.non_existent_update_url = reverse('inventory:blocked_sales_date_create_update', kwargs={'pk': cls.non_existent_pk})

    

#     def test_create_view_redirects_non_admin(self):
#         self.client.login(username='testuser', password='password123')
        
        
#         response_get = self.client.get(self.create_url)
#         self.assertRedirects(response_get, f'{reverse("users:login")}?next={self.create_url}')
        
        
#         response_post = self.client.post(self.create_url, data={})
#         self.assertRedirects(response_post, f'{reverse("users:login")}?next={self.create_url}')

#     def test_update_view_redirects_non_admin(self):
#         self.client.login(username='testuser', password='password123')
        
        
#         response_get = self.client.get(self.update_url)
#         self.assertRedirects(response_get, f'{reverse("users:login")}?next={self.update_url}')
        
        
#         response_post = self.client.post(self.update_url, data={})
#         self.assertRedirects(response_post, f'{reverse("users:login")}?next={self.update_url}')

    

#     def test_get_create_view_as_admin(self):
#         self.client.login(username='adminuser', password='adminpass123')
#         response = self.client.get(self.create_url)
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'inventory/admin_blocked_sales_date_create_update.html')
#         self.assertIn('form', response.context)
#         self.assertFalse(response.context['is_edit_mode'])
#         self.assertEqual(response.context['page_title'], "Create New Blocked Sales Date")

#     def test_get_update_view_as_admin(self):
#         self.client.login(username='adminuser', password='adminpass123')
#         response = self.client.get(self.update_url)
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'inventory/admin_blocked_sales_date_create_update.html')
#         self.assertIn('form', response.context)
#         self.assertTrue(response.context['is_edit_mode'])
#         self.assertEqual(response.context['form'].instance, self.blocked_date)
#         self.assertEqual(response.context['page_title'], "Edit Blocked Sales Date")

    
    
#     def test_post_create_view_success(self):
#         self.client.login(username='adminuser', password='adminpass123')
#         initial_count = BlockedSalesDate.objects.count()
        
#         post_data = {
#             'start_date': '2026-01-01',
#             'end_date': '2026-01-02',
#             'description': 'New Year Holiday'
#         }
        
#         response = self.client.post(self.create_url, data=post_data, follow=True)
        
#         self.assertRedirects(response, self.management_url)
#         self.assertEqual(BlockedSalesDate.objects.count(), initial_count + 1)
        
#         new_date = BlockedSalesDate.objects.get(description='New Year Holiday')
#         self.assertEqual(new_date.start_date, datetime.date(2026, 1, 1))

#         messages = list(get_messages(response.wsgi_request))
#         self.assertEqual(len(messages), 1)
#         self.assertEqual(str(messages[0]), f"Blocked sales date '{new_date}' created successfully.")

#     def test_post_create_view_invalid_data(self):
#         self.client.login(username='adminuser', password='adminpass123')
#         initial_count = BlockedSalesDate.objects.count()

#         post_data = {
#             'start_date': '2026-02-10',
#             'end_date': '2026-02-09', 
#             'description': 'Invalid period'
#         }

#         response = self.client.post(self.create_url, data=post_data)

#         self.assertEqual(response.status_code, 200) 
#         self.assertEqual(BlockedSalesDate.objects.count(), initial_count) 
#         self.assertIn('form', response.context)
#         self.assertTrue(response.context['form'].errors) 
#         self.assertIn('end_date', response.context['form'].errors)

#         messages = list(get_messages(response.wsgi_request))
#         self.assertEqual(len(messages), 1)
#         self.assertEqual(str(messages[0]), "Please correct the errors below.")

#     def test_post_update_view_success(self):
#         self.client.login(username='adminuser', password='adminpass123')

#         post_data = {
#             'start_date': self.blocked_date.start_date.strftime('%Y-%m-%d'),
#             'end_date': self.blocked_date.end_date.strftime('%Y-%m-%d'),
#             'description': 'Updated Christmas Break'
#         }

#         response = self.client.post(self.update_url, data=post_data, follow=True)
        
#         self.assertRedirects(response, self.management_url)
        
#         self.blocked_date.refresh_from_db()
#         self.assertEqual(self.blocked_date.description, 'Updated Christmas Break')

#         messages = list(get_messages(response.wsgi_request))
#         self.assertEqual(len(messages), 1)
#         self.assertEqual(str(messages[0]), f"Blocked sales date '{self.blocked_date}' updated successfully.")

#     def test_post_update_view_invalid_data(self):
#         self.client.login(username='adminuser', password='adminpass123')
#         original_description = self.blocked_date.description

#         post_data = {
#             'start_date': '2025-12-26',
#             'end_date': '2025-12-24', 
#             'description': 'This should not be saved'
#         }

#         response = self.client.post(self.update_url, data=post_data)

#         self.assertEqual(response.status_code, 200) 
#         self.blocked_date.refresh_from_db()
#         self.assertEqual(self.blocked_date.description, original_description) 
#         self.assertTrue(response.context['form'].errors)

    

#     def test_update_view_non_existent_pk_returns_404(self):
#         self.client.login(username='adminuser', password='adminpass123')
        
        
#         response_get = self.client.get(self.non_existent_update_url)
#         self.assertEqual(response_get.status_code, 404)
        
        
#         response_post = self.client.post(self.non_existent_update_url, data={})
#         self.assertEqual(response_post.status_code, 404)
