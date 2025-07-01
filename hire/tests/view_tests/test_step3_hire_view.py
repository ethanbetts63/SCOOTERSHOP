import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.messages import get_messages

                                                      
from hire.views.step3_AddonPackage_view import AddonPackageView
                                                               
from hire.hire_pricing import (
    calculate_motorcycle_hire_price,
    calculate_package_price,                    
    calculate_addon_price                    
)

from hire.tests.test_helpers.model_factories import (
    create_motorcycle, create_temp_hire_booking, create_addon, create_package,
    create_hire_settings, create_booking_addon, create_hire_booking,
    create_temp_booking_addon
)
from hire.models import TempHireBooking, TempBookingAddOn, Package, AddOn
from dashboard.models import HireSettings
from inventory.models import Motorcycle

class AddonPackageViewTest(TestCase):
    """
    Tests for the AddonPackageView (Step 3 of the hire booking process).
    This class focuses on testing the view's logic, interactions with the session,
    and updates to the TempHireBooking and TempBookingAddOn models,
    assuming that models and forms are already correctly tested.
    """

    def setUp(self):
        """
        Set up common test data and configurations before each test method.
        """
        self.client = Client()
                                                                               
        self.hire_settings = create_hire_settings(
            packages_enabled=True,
            add_ons_enabled=True,
            default_daily_rate=Decimal('100.00'),                                   
            default_hourly_rate=Decimal('20.00'),                                    
        )
                                                
        self.motorcycle = create_motorcycle(
            engine_size=250,
            daily_hire_rate=Decimal('100.00'),
            hourly_hire_rate=Decimal('20.00')                                         
        )
        
                                                  
        self.temp_booking_data = {
            'pickup_date': timezone.now().date() + datetime.timedelta(days=1),
            'pickup_time': datetime.time(9, 0),
            'return_date': timezone.now().date() + datetime.timedelta(days=3),                      
            'return_time': datetime.time(17, 0),
            'has_motorcycle_license': True,
        }
                                             
        self.temp_booking = create_temp_hire_booking(**self.temp_booking_data)
        
                                                                                
        self.temp_booking.motorcycle = self.motorcycle
        
                                                                                   
        self.temp_booking.total_hire_price = calculate_motorcycle_hire_price(
            self.motorcycle,
            self.temp_booking.pickup_date,
            self.temp_booking.return_date,
            self.temp_booking.pickup_time,
            self.temp_booking.return_time,
            self.hire_settings
        )
        self.temp_booking.save()                                

                                                                                    
        self.session = self.client.session
        self.session['temp_booking_uuid'] = str(self.temp_booking.session_uuid)
        self.session.save()

                                                     
        self.addon1 = create_addon(name="Helmet", daily_cost=Decimal('10.00'), hourly_cost=Decimal('2.00'), min_quantity=1, max_quantity=2)
        self.addon2 = create_addon(name="Jacket", daily_cost=Decimal('20.00'), hourly_cost=Decimal('4.00'), min_quantity=1, max_quantity=1)                                             
        self.addon3 = create_addon(name="Gloves", daily_cost=Decimal('5.00'), hourly_cost=Decimal('1.00'), min_quantity=1, max_quantity=3)
        self.addon_unavailable = create_addon(name="GPS", daily_cost=Decimal('15.00'), hourly_cost=Decimal('3.00'), is_available=False)

                                                      
                                                                               
        self.package1 = create_package(name="Standard Pack", daily_cost=Decimal('30.00'), hourly_cost=Decimal('6.00'), add_ons=[self.addon1, self.addon2]) 
        self.package2 = create_package(name="Premium Pack", daily_cost=Decimal('70.00'), hourly_cost=Decimal('14.00'), add_ons=[self.addon1, self.addon2, self.addon3])
        self.package_unavailable = create_package(name="Old Pack", daily_cost=Decimal('20.00'), hourly_cost=Decimal('4.00'), is_available=False)

                               

    def test_get_redirects_if_no_temp_booking(self):
        """
        Test that a GET request redirects to step2 if no temp_booking_uuid is found in the session.
        """
                                                                        
                                                              
        if self.temp_booking:
            self.temp_booking.delete()

        del self.client.session['temp_booking_uuid']                                   
        self.client.session.save()
        
                                                                                                     
        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))
        self.assertRedirects(response, reverse('hire:step2_choose_bike'))
        
                                                
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 0)

    def test_get_with_invalid_motorcycle_id(self):
        """
        Test that a GET request with an invalid motorcycle_id redirects to step2 and shows an error message.
        """
        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[99999]))                        
        self.assertRedirects(response, reverse('hire:step2_choose_bike'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Selected motorcycle not found.")

    def test_get_with_unavailable_motorcycle(self):
        """
        Test that a GET request with a motorcycle that is not available (e.g., status is_available=False)
        redirects to step2 and shows an error message.
        """
        unavailable_motorcycle = create_motorcycle(is_available=False, engine_size=250)
        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[unavailable_motorcycle.id]))
        self.assertRedirects(response, reverse('hire:step2_choose_bike'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
                                                                            
        self.assertEqual(str(messages[0]), "The selected motorcycle is currently not available.")

    def test_get_with_motorcycle_no_license(self):
        """
        Test that a GET request with a motorcycle requiring a full license (engine_size > 50)
        redirects to step2 and shows an error if the temp_booking indicates no motorcycle license.
        """
        self.temp_booking.has_motorcycle_license = False                              
        self.temp_booking.save()
        motorcycle_large_engine = create_motorcycle(engine_size=600)                                          
        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[motorcycle_large_engine.id]))
        self.assertRedirects(response, reverse('hire:step2_choose_bike'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "You require a full motorcycle license for this motorcycle.")

    def test_get_with_valid_motorcycle_id_updates_temp_booking(self):
        """
        Test that a GET request with a valid motorcycle_id updates the temp_booking
        with the selected motorcycle and calculates the total_hire_price, then renders the form.
        """
                                                                                              
        fresh_temp_booking = create_temp_hire_booking(**self.temp_booking_data)
        self.session['temp_booking_uuid'] = str(fresh_temp_booking.session_uuid)
        self.session.save()

        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, AddonPackageView.template_name)                                      
        
        fresh_temp_booking.refresh_from_db()                                                      
        self.assertEqual(fresh_temp_booking.motorcycle, self.motorcycle)
        self.assertGreater(fresh_temp_booking.total_hire_price, Decimal('0.00'))                                                        

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), f"Motorcycle {self.motorcycle.model} selected successfully. Now choose add-ons and packages.")

    def test_get_renders_form_with_existing_temp_booking_no_motorcycle_id(self):
        """
        Test that a GET request without a motorcycle_id (simulating a user returning to step 3)
        renders the form correctly with existing temp_booking data.
        """
                                                                                       
        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))                     
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, AddonPackageView.template_name)
        self.assertContains(response, self.motorcycle.model)                                                                  

    def test_get_packages_enabled_and_no_custom_packages(self):
        """
        Test that if packages are enabled but no custom packages exist, a 'Basic Hire' package
        is automatically created/ensured and selected for the temp_booking.
        """
        Package.objects.all().delete()                                                             
        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))
        self.assertEqual(response.status_code, 200)
        
        basic_package = Package.objects.get(name="Basic Hire")                             
        self.assertIsNotNone(basic_package)
        self.assertEqual(basic_package.daily_cost, Decimal('0.00'))                             
        self.assertEqual(basic_package.hourly_cost, Decimal('0.00'))                            
        
        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.package, basic_package)                                   
        self.assertEqual(self.temp_booking.total_package_price, Decimal('0.00'))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("No custom packages found, a default 'Basic Hire' package has been selected." in str(m) for m in messages))

    def test_get_packages_enabled_and_custom_packages_exist(self):
        """
        Test that if packages are enabled and custom packages exist, they are displayed in the form,
        and the temp_booking defaults to one of the available packages if none was previously selected.
        """
                                                                              
        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.package1.name)
        self.assertContains(response, self.package2.name)
        self.assertNotContains(response, self.package_unavailable.name)                                          

        self.temp_booking.refresh_from_db()
                                                                                          
                                                                        
        available_packages_names = [p.name for p in Package.objects.filter(is_available=True)]
        self.assertIn(self.temp_booking.package.name, available_packages_names)

    def test_get_packages_disabled(self):
        """
        Test that if packages are disabled in HireSettings, no packages are shown in the form,
        and the temp_booking's package and total_package_price are cleared.
        """
        self.hire_settings.packages_enabled = False                   
        self.hire_settings.save()
        
                                                                        
        self.temp_booking.package = self.package1
        self.temp_booking.total_package_price = self.package1.daily_cost                             
        self.temp_booking.save()

        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.package1.name)                                        
        self.assertNotContains(response, self.package2.name)

        self.temp_booking.refresh_from_db()
        self.assertIsNone(self.temp_booking.package)                            
        self.assertEqual(self.temp_booking.total_package_price, Decimal('0.00'))                       

    def test_get_addons_enabled(self):
        """
        Test that if add-ons are enabled, active add-ons are displayed in the form.
        """
        self.addon_unavailable.refresh_from_db()                            
        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.addon1.name)
        self.assertContains(response, self.addon2.name) 
        self.assertContains(response, self.addon3.name)
        self.assertNotContains(response, self.addon_unavailable.name)                                         

    def test_get_addons_disabled(self):
        """
        Test that if add-ons are disabled in HireSettings, no add-ons are shown in the form.
        """
        self.hire_settings.add_ons_enabled = False                  
        self.hire_settings.packages_enabled = False                                      
        self.hire_settings.save()
        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))
        self.assertEqual(response.status_code, 200)
                                                                                 
                                                 
                                                   
        self.assertNotContains(response, self.addon1.name)                                       
        self.assertNotContains(response, self.addon2.name)
        self.assertNotContains(response, self.addon3.name)

    def test_get_initial_data_population_for_addons_and_package(self):
        """
        Test that previously selected add-ons and packages stored in TempHireBooking
        and TempBookingAddOn are correctly pre-filled in the form when the page loads.
        """
                                                                                       
        self.temp_booking.package = self.package1                                   
        self.temp_booking.save()

                                              
        create_temp_booking_addon(self.temp_booking, self.addon1, quantity=2)                                  
        create_temp_booking_addon(self.temp_booking, self.addon3, quantity=1)                                  

        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))                     
        self.assertEqual(response.status_code, 200)

        form = response.context['form']
                                                    
        self.assertEqual(form['package'].value(), self.package1.id)                                   
        
                                                                 
        self.assertTrue(form[f'addon_{self.addon1.id}_selected'].value())
        self.assertEqual(form[f'addon_{self.addon1.id}_quantity'].value(), 2)
        
                                                                 
        self.assertTrue(form[f'addon_{self.addon3.id}_selected'].value())
        self.assertEqual(form[f'addon_{self.addon3.id}_quantity'].value(), 1)
        
                                                       
                                                                                                        
                                                                                   
        self.assertNotIn(f'addon_{self.addon2.id}_selected', form.fields)
        self.assertNotIn(f'addon_{self.addon2.id}_quantity', form.fields)


                                

    def test_post_redirects_if_no_temp_booking(self):
        """
        Test that a POST request redirects to step2 if no temp_booking_uuid is found in the session.
        """
                                                           
        TempHireBooking.objects.filter(session_uuid=self.temp_booking.session_uuid).delete()
        del self.client.session['temp_booking_uuid']
        self.client.session.save()

                                                                         
        response = self.client.post(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]), {})
        self.assertEqual(response.status_code, 302)                    
        self.assertEqual(response.url, reverse('hire:step2_choose_bike'))                                  
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Session expired. Please start again.")

    def test_post_valid_submission_no_addons_no_package(self):
        """
        Test a valid POST submission where no add-ons or packages are selected.
        Ensures prices are updated correctly and redirects to the next step.
        """
                                                                                       
        form_data = {}                                            
        response = self.client.post(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]), form_data)
        self.assertEqual(response.status_code, 302)                    
        self.assertEqual(response.url, reverse('hire:step4_no_account'))                                  

        self.temp_booking.refresh_from_db()                                
        self.assertIsNone(self.temp_booking.package)                                
        self.assertEqual(self.temp_booking.total_package_price, Decimal('0.00'))
        self.assertEqual(self.temp_booking.total_addons_price, Decimal('0.00'))
                                                                           
        self.assertEqual(self.temp_booking.grand_total, self.temp_booking.total_hire_price) 
        self.assertEqual(self.temp_booking.temp_booking_addons.count(), 0)                                    

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Add-ons and packages updated successfully.")

    def test_post_valid_submission_with_package_and_addons(self):
        """
        Test a valid POST submission with a package and additional add-ons selected.
        Verifies correct price calculations and temporary add-on creation.
        """
                                                                                       
                                                                                                 
                                                                       
                                                                               
        form_data = {
            'package': self.package1.id,
            f'addon_{self.addon1.id}_selected': 'on',
            f'addon_{self.addon1.id}_quantity': 1,                      
            f'addon_{self.addon3.id}_selected': 'on',
            f'addon_{self.addon3.id}_quantity': 2,           
        }
        response = self.client.post(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]), form_data)
        self.assertEqual(response.status_code, 302)                    
        self.assertEqual(response.url, reverse('hire:step4_no_account'))                                  

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.package, self.package1)
        
                                                                                 
        expected_package_price = calculate_package_price(
            package_instance=self.package1,
            pickup_date=self.temp_booking.pickup_date,
            return_date=self.temp_booking.return_date,
            pickup_time=self.temp_booking.pickup_time,
            return_time=self.temp_booking.return_time,
            hire_settings=self.hire_settings
        )
        self.assertEqual(self.temp_booking.total_package_price, expected_package_price)

                                                                                                           
                                                                               
                                                                     
        expected_addon1_price = calculate_addon_price(
            addon_instance=self.addon1,
            quantity=1,
            pickup_date=self.temp_booking.pickup_date,
            return_date=self.temp_booking.return_date,
            pickup_time=self.temp_booking.pickup_time,
            return_time=self.temp_booking.return_time,
            hire_settings=self.hire_settings
        )
        expected_addon3_price = calculate_addon_price(
            addon_instance=self.addon3,
            quantity=2,
            pickup_date=self.temp_booking.pickup_date,
            return_date=self.temp_booking.return_date,
            pickup_time=self.temp_booking.pickup_time,
            return_time=self.temp_booking.return_time,
            hire_settings=self.hire_settings
        )
        expected_total_addons_price = expected_addon1_price + expected_addon3_price
        self.assertEqual(self.temp_booking.total_addons_price, expected_total_addons_price)
        
                                                                                                     
        expected_grand_total = self.temp_booking.total_hire_price + expected_package_price + expected_total_addons_price
        self.assertEqual(self.temp_booking.grand_total, expected_grand_total)

        self.assertEqual(self.temp_booking.temp_booking_addons.count(), 2)                                          
        addon1_temp = self.temp_booking.temp_booking_addons.get(addon=self.addon1)
        self.assertEqual(addon1_temp.quantity, 1)
        addon3_temp = self.temp_booking.temp_booking_addons.get(addon=self.addon3)
        self.assertEqual(addon3_temp.quantity, 2)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Add-ons and packages updated successfully.")

    def test_post_invalid_submission_addon_quantity_too_high(self):
        """
        Test a POST submission where an add-on quantity exceeds its adjusted maximum allowed.
        The form should show an error, and no changes should be saved to temp_booking.
        """
                                                                                       
        form_data = {
            'package': self.package1.id,
            f'addon_{self.addon1.id}_selected': 'on',
            f'addon_{self.addon1.id}_quantity': 2,                                                                                              
        }
        response = self.client.post(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]), form_data)
        self.assertEqual(response.status_code, 200)                                        
        self.assertTemplateUsed(response, AddonPackageView.template_name)

        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn(f'addon_{self.addon1.id}_quantity', form.errors)
                                                                                               
        self.assertIn("Ensure this value is less than or equal to 1.", form.errors[f'addon_{self.addon1.id}_quantity'][0])

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please correct the errors below.")

                                                                                         
        self.temp_booking.refresh_from_db()
                                                                                                 
                                                                  
        self.assertIsNone(self.temp_booking.package) 
        self.assertEqual(self.temp_booking.total_addons_price, Decimal('0.00'))
        self.assertEqual(self.temp_booking.temp_booking_addons.count(), 0)

                                                                                          
                                                                          
                                                    

    def test_post_invalid_submission_unavailable_package_selected(self):
        """
        Test a POST submission where an unavailable package is attempted to be selected.
        The form should show an error.
        """
                                                                                       
        form_data = {
            'package': self.package_unavailable.id,                                           
        }
        response = self.client.post(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, AddonPackageView.template_name)

        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('package', form.errors)
                                                                                   
        self.assertIn("Select a valid choice. That choice is not one of the available choices.", form.errors['package'][0])

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please correct the errors below.")

    def test_post_clears_previous_addons_on_successful_submission(self):
        """
        Test that existing TempBookingAddOn instances associated with the temp_booking
        are cleared before new ones are added during a successful POST submission.
        """
                                                                                       
                                                                          
        existing_addon_temp_booking = create_temp_booking_addon(self.temp_booking, self.addon3, quantity=1)
        self.assertEqual(self.temp_booking.temp_booking_addons.count(), 1)

        form_data = {
            'package': self.package1.id,
            f'addon_{self.addon1.id}_selected': 'on',
            f'addon_{self.addon1.id}_quantity': 1,
        }
        response = self.client.post(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]), form_data)
        self.assertEqual(response.status_code, 302)                    
        self.assertEqual(response.url, reverse('hire:step4_no_account'))                                  

        self.temp_booking.refresh_from_db()
        self.assertEqual(self.temp_booking.temp_booking_addons.count(), 1)                                           
                                                          
        self.assertFalse(TempBookingAddOn.objects.filter(id=existing_addon_temp_booking.id).exists())
                                                           
        self.assertTrue(self.temp_booking.temp_booking_addons.filter(addon=self.addon1).exists())

    def test_post_redirects_to_has_account_for_authenticated_user(self):
        """
        Test that a successful POST submission redirects to step4_has_account
        if the user is authenticated.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')                  

                                                                                       
        form_data = {}                         
        response = self.client.post(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]), form_data)
        self.assertEqual(response.status_code, 302)                    
        self.assertEqual(response.url, reverse('hire:step4_has_account'))                                  

    def test_post_redirects_to_no_account_for_anonymous_user(self):
        """
        Test that a successful POST submission redirects to step4_no_account
        if the user is anonymous (not logged in).
        """
                                               
                                                                                       
        form_data = {}                         
        response = self.client.post(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]), form_data)
        self.assertEqual(response.status_code, 302)                    
        self.assertEqual(response.url, reverse('hire:step4_no_account'))                                  

    def test_get_motorcycle_with_conflicting_booking(self):
        """
        Test that a GET request with a motorcycle that has an overlapping HireBooking
        redirects to step2 and shows an error, indicating unavailability.
        """
                                                                   
        create_hire_booking(
            motorcycle=self.motorcycle,
            pickup_date=self.temp_booking.pickup_date,
            return_date=self.temp_booking.return_date + datetime.timedelta(days=1),                             
            pickup_time=self.temp_booking.pickup_time,
            return_time=self.temp_booking.return_time
        )

        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))
        self.assertRedirects(response, reverse('hire:step2_choose_bike'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
                                                                            
        self.assertEqual(str(messages[0]), "The selected motorcycle is not available for your chosen dates/times due to an existing booking.")

    def test_get_motorcycle_with_missing_pickup_date_in_temp_booking(self):
        """
        Test that a GET request redirects to step2 and shows an error if the
        temp_booking has a missing pickup_date.
        """
                                       
        self.temp_booking.pickup_date = None 
        self.temp_booking.save()

        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))
        self.assertRedirects(response, reverse('hire:step2_choose_bike'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please select valid pickup and return dates/times first.")

    def test_get_motorcycle_with_return_date_before_pickup_date_in_temp_booking(self):
        """
        Test that a GET request redirects to step2 and shows an error if the
        temp_booking has a return_date before the pickup_date.
        """
                                                  
        self.temp_booking.pickup_date = timezone.now().date()
        self.temp_booking.return_date = timezone.now().date() - datetime.timedelta(days=1) 
        self.temp_booking.save()

        response = self.client.get(reverse('hire:step3_addons_and_packages', args=[self.motorcycle.id]))
        self.assertRedirects(response, reverse('hire:step2_choose_bike'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
                                                                            
        self.assertEqual(str(messages[0]), "Return time must be after pickup time.")

