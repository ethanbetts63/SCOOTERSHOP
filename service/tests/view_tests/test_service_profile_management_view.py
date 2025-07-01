from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone                                          

                         
from service.models import ServiceProfile
from ..test_helpers.model_factories import UserFactory, ServiceProfileFactory

class ServiceProfileManagementViewTest(TestCase):
    """
    Tests for the ServiceProfileManagementView.
    Covers access control, listing (initial paginated display), and form submission (create via management view).
    Search functionality tests are removed as they are now handled by AJAX in the frontend
    and the dedicated `ajax_search_service_profiles` view.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods.
        Create various users and service profiles for testing different scenarios.
        """
        cls.staff_user = UserFactory(username='staff_user', is_staff=True, is_superuser=False)
        cls.superuser = UserFactory(username='superuser', is_staff=True, is_superuser=True)
        cls.regular_user = UserFactory(username='regular_user', is_staff=False, is_superuser=False)

                                                                        
                                                                         
        cls.profile1 = ServiceProfileFactory(
            name="Alpha Profile", email="alpha@example.com", phone_number="1112223333",
            city="Springville",
            created_at=timezone.now() - timezone.timedelta(days=30),
            user=UserFactory(username='alpha_user')
        )
        cls.profile2 = ServiceProfileFactory(
            name="Beta Profile", email="beta@test.com", phone_number="4445556666",
            city="Shelbyville",
            created_at=timezone.now() - timezone.timedelta(days=20),
            user=UserFactory(username='beta_user')
        )
        cls.profile3 = ServiceProfileFactory(
            name="Gamma Profile", email="gamma@domain.net", phone_number="7778889999",
            address_line_1="123 Main St", country="US",
            created_at=timezone.now() - timezone.timedelta(days=10),
            user=None                              
        )
        cls.profile_new = ServiceProfileFactory(
            name="Newest Profile", email="newest@domain.com", phone_number="0001112222",
            city="New City", created_at=timezone.now(),
            user=UserFactory(username='newest_user')
        )

                                                                                
        cls.unlinked_user = UserFactory(username='unlinked_user_for_form', email='unlinked_form@example.com')


                                                  
        cls.list_url = reverse('service:admin_service_profiles')
                                                                                              
                                                                                                    
        cls.edit_url_name = 'service:admin_edit_service_profile'
        cls.delete_url_name = 'service:admin_delete_service_profile'


    def setUp(self):
        """
        Set up for each test method.
        Initialize client and session.
        """
        self.client = Client()
                                                              
        self.session = self.client.session
        self.session.save()


                                                                            

    def test_view_redirects_anonymous_user(self):
        """
        Ensure anonymous users are redirected to the login page for management view.
        """
        response = self.client.get(self.list_url)
        self.assertRedirects(response, reverse('users:login') + f'?next={self.list_url}')

    def test_view_denies_access_to_regular_user(self):
        """
        Ensure regular (non-staff/non-superuser) users are denied access to management view.
        """
        self.client.force_login(self.regular_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 403)            

    def test_view_grants_access_to_staff_user(self):
        """
        Ensure staff users can access the management view.
        """
        self.client.force_login(self.staff_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)

    def test_view_grants_access_to_superuser(self):
        """
        Ensure superusers can access the management view.
        """
        self.client.force_login(self.superuser)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)


                                                      

    def test_get_request_list_all_profiles_with_pagination(self):
        """
        Test GET request to list all service profiles, verifying pagination.
        The view should now always return paginated results for the full list.
        """
        self.client.force_login(self.staff_user)
                                                            
        for i in range(15):                                                       
            ServiceProfileFactory(
                name=f"Paginated Profile {i}",
                created_at=timezone.now() - timezone.timedelta(minutes=i)
            )

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'service/admin_service_profile_management.html')
        
        self.assertIn('profiles', response.context)
        self.assertIn('page_obj', response.context)
        self.assertTrue(response.context['is_paginated'])                          
        self.assertEqual(response.context['page_obj'].number, 1)                        
        self.assertEqual(len(response.context['page_obj'].object_list), 10)                    

                                                                                    
        expected_profiles = list(ServiceProfile.objects.all().order_by('-created_at'))
        self.assertListEqual(list(response.context['profiles']), expected_profiles[:10])

        self.assertEqual(response.context['search_term'], '')                                   

    def test_get_request_list_profiles_specific_page(self):
        """
        Test GET request to list service profiles on a specific page.
        """
        self.client.force_login(self.staff_user)
                                                   
        total_profiles = 25
        for i in range(total_profiles):
            ServiceProfileFactory(
                name=f"Paginated Profile {i}",
                created_at=timezone.now() - timezone.timedelta(minutes=i)
            )

                                 
        response = self.client.get(f"{self.list_url}?page=2")

        self.assertEqual(response.status_code, 200)
        self.assertIn('profiles', response.context)
        self.assertEqual(response.context['page_obj'].number, 2)
                                                                           
        self.assertEqual(len(response.context['page_obj'].object_list), 10)

        expected_profiles = list(ServiceProfile.objects.all().order_by('-created_at'))
        self.assertListEqual(list(response.context['profiles']), expected_profiles[10:20])


    def test_get_request_edit_mode(self):
        """
        Test GET request to display the management view with a specific profile
        loaded into the form for editing.
        Note: The form displayed on the management page is the same AdminServiceProfileForm,
        but the POST for actual update happens via a separate URL (admin_edit_service_profile)
        handled by ServiceProfileCreateUpdateView. This test focuses on the GET display.
        """
        self.client.force_login(self.staff_user)
                                                                                           
        edit_url = reverse(self.edit_url_name, kwargs={'pk': self.profile1.pk})
        response = self.client.get(edit_url)                                                               

        self.assertEqual(response.status_code, 200)
                                                                                            
                                                                        
        self.assertTemplateUsed(response, 'service/admin_service_profile_form.html')
        self.assertIn('form', response.context)
        self.assertTrue(response.context['is_edit_mode'])
        self.assertEqual(response.context['current_profile'], self.profile1)
        self.assertEqual(response.context['form'].instance, self.profile1)
        self.assertFalse(response.context['form'].is_bound)                                                


    def test_get_request_edit_mode_non_existent_profile(self):
        """
        Test GET request to edit a non-existent profile. Should return 404.
        """
        self.client.force_login(self.staff_user)
        non_existent_pk = self.profile1.pk + 9999
                                                              
        edit_url = reverse(self.edit_url_name, kwargs={'pk': non_existent_pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 404)


                                                                          
                                                                      
                                                        

    def test_post_request_create_profile_valid(self):
        """
        Test valid POST request to create a new profile from the management view (list page).
        """
        self.client.force_login(self.staff_user)
        initial_count = ServiceProfile.objects.count()
        new_profile_data = {
            'user': self.unlinked_user.pk,
            'name': 'New Profile From Mgmt',
            'email': 'mgmt_create@example.com',
            'phone_number': '1234512345',
            'address_line_1': '1 Mgmt St',
            'city': 'Mgmtville',
            'state': 'MG',
            'post_code': '12345',
            'country': 'US',
        }
                                                                                   
        response = self.client.post(self.list_url, new_profile_data, follow=True)                  

        self.assertEqual(ServiceProfile.objects.count(), initial_count + 1)
        new_profile = ServiceProfile.objects.get(name='New Profile From Mgmt')
        self.assertRedirects(response, self.list_url)
        
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f"Service Profile for '{new_profile.name}' created successfully.")
        self.assertEqual(messages_list[0].level, messages.SUCCESS)


    def test_post_request_create_profile_invalid(self):
        """
        Test invalid POST request to create a new profile from the management view (list page).
        """
        self.client.force_login(self.staff_user)
        initial_count = ServiceProfile.objects.count()
        invalid_data = {
            'user': '',          
            'name': '',                                     
            'email': 'invalid@example.com',
            'phone_number': '1234567890',
            'address_line_1': '1 Invalid St',
            'city': 'Invalidton',
            'state': 'IV',
            'post_code': '00000',
            'country': 'US',
        }
                                                       
        response = self.client.post(self.list_url, invalid_data)

        self.assertEqual(ServiceProfile.objects.count(), initial_count)                 
        self.assertEqual(response.status_code, 200)                               
        self.assertTemplateUsed(response, 'service/admin_service_profile_management.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('name', response.context['form'].errors)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Please correct the errors below.")
        self.assertEqual(messages_list[0].level, messages.ERROR)


class ServiceProfileDeleteViewTest(TestCase):
    """
    Tests for the ServiceProfileDeleteView.
    """

    @classmethod
    def setUpTestData(cls):
        cls.staff_user = UserFactory(username='staff_user', is_staff=True, is_superuser=False)
        cls.superuser = UserFactory(username='superuser', is_staff=True, is_superuser=True)
        cls.regular_user = UserFactory(username='regular_user', is_staff=False, is_superuser=False)
        cls.profile_to_delete = ServiceProfileFactory(name="Profile to Delete")
        cls.list_url = reverse('service:admin_service_profiles')
        cls.delete_url_name = 'service:admin_delete_service_profile'


    def setUp(self):
        self.client = Client()
                                                              
        self.session = self.client.session
        self.session.save()

                                  

    def test_view_redirects_anonymous_user(self):
        """
        Ensure anonymous users are redirected to login for delete view.
        """
        delete_url = reverse(self.delete_url_name, kwargs={'pk': self.profile_to_delete.pk})
        response = self.client.post(delete_url)
        self.assertRedirects(response, reverse('users:login') + f'?next={delete_url}')

    def test_view_denies_access_to_regular_user(self):
        """
        Ensure regular users are denied access to delete view.
        """
        self.client.force_login(self.regular_user)
        delete_url = reverse(self.delete_url_name, kwargs={'pk': self.profile_to_delete.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 403)

    def test_view_grants_access_to_staff_user(self):
        """
        Ensure staff users can access delete view.
        (This test implicitly passes if the POST test below passes, as GET isn't typically used for delete).
        """
        self.client.force_login(self.staff_user)
                                                                                    
        delete_url = reverse(self.delete_url_name, kwargs={'pk': self.profile_to_delete.pk})
        response = self.client.get(delete_url)                                            
        self.assertEqual(response.status_code, 405)                             


                                           

    def test_post_request_delete_profile_valid(self):
        """
        Test valid POST request to delete a ServiceProfile.
        """
        self.client.force_login(self.staff_user)
        profile_pk = self.profile_to_delete.pk
        profile_name = self.profile_to_delete.name
        initial_count = ServiceProfile.objects.count()

        delete_url = reverse(self.delete_url_name, kwargs={'pk': profile_pk})
        response = self.client.post(delete_url, follow=True)                  

        self.assertEqual(ServiceProfile.objects.count(), initial_count - 1)
        self.assertFalse(ServiceProfile.objects.filter(pk=profile_pk).exists())
        self.assertRedirects(response, self.list_url)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f"Service Profile for '{profile_name}' deleted successfully.")
        self.assertEqual(messages_list[0].level, messages.SUCCESS)

    def test_post_request_delete_non_existent_profile(self):
        """
        Test POST request to delete a non-existent ServiceProfile. Should return 404.
        """
        self.client.force_login(self.staff_user)
        non_existent_pk = self.profile_to_delete.pk + 9999
        delete_url = reverse(self.delete_url_name, kwargs={'pk': non_existent_pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 404)
