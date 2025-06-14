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

        # Create an InventorySettings instance (singleton)
        cls.inventory_settings = InventorySettingsFactory()

        # Create a condition for our motorcycle
        cls.condition_used = MotorcycleConditionFactory(name='used', display_name='Used')

        # Create a test motorcycle
        cls.motorcycle = MotorcycleFactory(
            brand='TestBrand',
            model='TestModel',
            year=2023,
            price=15000.00,
            conditions=[cls.condition_used.name], # Assign the condition
            is_available=True
        )
        # Create another motorcycle to ensure we are retrieving the correct one
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
        # Get the URL for the test motorcycle
        url = reverse('inventory:motorcycle-detail', kwargs={'pk': self.motorcycle.pk})
        response = self.client.get(url)

        # Assert status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # Assert the correct template is used
        self.assertTemplateUsed(response, 'inventory/user_motorcycle_details.html')

        # Assert the motorcycle object is in the context and is the correct one
        self.assertIn('motorcycle', response.context)
        self.assertEqual(response.context['motorcycle'], self.motorcycle)

        # Assert InventorySettings are in the context
        self.assertIn('inventory_settings', response.context)
        self.assertEqual(response.context['inventory_settings'], self.inventory_settings)

        # Assert that motorcycle details are displayed on the page
        self.assertContains(response, self.motorcycle.title)
        self.assertContains(response, str(self.motorcycle.price))
        self.assertContains(response, self.motorcycle.description)


    def test_motorcycle_details_view_404_not_found(self):
        """
        Test that accessing a non-existent motorcycle PK raises a 404 error.
        """
        # Use a PK that does not exist (e.g., one greater than any created)
        non_existent_pk = self.motorcycle.pk + 999

        url = reverse('inventory:motorcycle-detail', kwargs={'pk': non_existent_pk})

        # Assert that the response status code is 404
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # Assert that the expected error message is present in the response content
        # Use 'in' operator with response.content.decode() for more robust check on 404 pages


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
            is_available=False # Set to unavailable
        )
        url = reverse('inventory:motorcycle-detail', kwargs={'pk': unavailable_motorcycle.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('motorcycle', response.context)
        self.assertEqual(response.context['motorcycle'], unavailable_motorcycle)
        self.assertContains(response, unavailable_motorcycle.title)
