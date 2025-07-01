from django.test import TestCase, Client
from django.urls import reverse
from ...test_helpers.model_factories import MotorcycleFactory, InventorySettingsFactory, MotorcycleConditionFactory

class UserMotorcycleDetailsViewTest(TestCase):
    """
    Tests for the UserMotorcycleDetailsView.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.client = Client()

                                                          
        cls.inventory_settings = InventorySettingsFactory()

                                               
        cls.condition_used = MotorcycleConditionFactory(name='used', display_name='Used')

                                  
        cls.motorcycle = MotorcycleFactory(
            brand='TestBrand',
            model='TestModel',
            year=2023,
            price=15000.00,
            conditions=[cls.condition_used.name],                       
            is_available=True
        )
                                                                               
        cls.other_motorcycle = MotorcycleFactory(
            brand='OtherBrand',
            model='OtherModel',
            year=2022,
            price=10000.00,
            is_available=True
        )


    def test_motorcycle_details_view_success(self):
        """
        Test that the motorcycle details page loads successfully with the correct context.
        """
                                             
        url = reverse('inventory:motorcycle-detail', kwargs={'pk': self.motorcycle.pk})
        response = self.client.get(url)

                                        
        self.assertEqual(response.status_code, 200)

                                             
        self.assertTemplateUsed(response, 'inventory/user_motorcycle_details.html')

                                                                               
        self.assertIn('motorcycle', response.context)
        self.assertEqual(response.context['motorcycle'], self.motorcycle)

                                                     
        self.assertIn('inventory_settings', response.context)
        self.assertEqual(response.context['inventory_settings'], self.inventory_settings)

                                                                  
        self.assertContains(response, self.motorcycle.title)
        self.assertContains(response, str(self.motorcycle.price))
        self.assertContains(response, self.motorcycle.description)


    def test_motorcycle_details_view_404_not_found(self):
        """
        Test that accessing a non-existent motorcycle PK raises a 404 error.
        """
                                                                           
        non_existent_pk = self.motorcycle.pk + 999

        url = reverse('inventory:motorcycle-detail', kwargs={'pk': non_existent_pk})

                                                     
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

                                                                                   
                                                                                             


    def test_motorcycle_details_view_unavailable_motorcycle(self):
        """
        Test that an unavailable motorcycle (is_available=False) still shows its details.
        The get_motorcycle_details utility handles this, returning the object regardless
        of availability, as the details page should show the item's info even if it's sold.
        """
        unavailable_motorcycle = MotorcycleFactory(
            brand='SoldBrand',
            model='SoldModel',
            year=2021,
            price=20000.00,
            is_available=False                     
        )
        url = reverse('inventory:motorcycle-detail', kwargs={'pk': unavailable_motorcycle.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('motorcycle', response.context)
        self.assertEqual(response.context['motorcycle'], unavailable_motorcycle)
        self.assertContains(response, unavailable_motorcycle.title)
