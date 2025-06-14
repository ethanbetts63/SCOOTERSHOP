# SCOOTER_SHOP/inventory/tests/admin_views/test_motorcycle_delete_view.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages
from unittest import mock

# Import the Motorcycle model
from inventory.models import Motorcycle

# Import factories for creating test data
from ...test_helpers.model_factories import MotorcycleFactory, UserFactory

class MotorcycleDeleteViewTest(TestCase):
    """
    Tests for the MotorcycleDeleteView.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Set up common data for all tests in this class.
        """
        cls.client = Client()
        # Create an admin user for authentication
        cls.admin_user = UserFactory(username='admin', email='admin@example.com', is_staff=True, is_superuser=True)
        cls.admin_user.set_password('adminpassword')
        cls.admin_user.save()

        # Create a non-admin user
        cls.non_admin_user = UserFactory(username='user', email='user@example.com', is_staff=False, is_superuser=False)
        cls.non_admin_user.set_password('userpassword')
        cls.non_admin_user.save()

        # Create a motorcycle to be deleted
        cls.motorcycle_to_delete = MotorcycleFactory(title='Test Motorcycle Delete', stock_number='DEL001')
        # Corrected URL name: 'admin_motorcycle_delete'
        cls.delete_url = reverse('inventory:admin_motorcycle_delete', kwargs={'pk': cls.motorcycle_to_delete.pk})

    def test_delete_motorcycle_as_admin_success(self):
        """
        Test that an admin user can successfully delete a motorcycle.
        """
        # Log in as admin
        self.client.login(username='admin', password='adminpassword')

        # Ensure the motorcycle exists before deletion attempt
        self.assertTrue(Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists())
        initial_motorcycle_count = Motorcycle.objects.count()

        # Perform the POST request to delete the motorcycle
        response = self.client.post(self.delete_url, follow=True)

        # Check for successful redirection
        self.assertRedirects(response, reverse('inventory:admin_inventory_management'))

        # Check if the motorcycle count has decreased by one
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count - 1)

        # Verify the motorcycle is no longer in the database
        self.assertFalse(Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists())

        # Check for success message
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), f'Motorcycle "{self.motorcycle_to_delete.title}" deleted successfully!')

    def test_delete_motorcycle_as_admin_not_found(self):
        """
        Test that an admin user attempting to delete a non-existent motorcycle
        results in a 404.
        """
        self.client.login(username='admin', password='adminpassword')
        non_existent_pk = self.motorcycle_to_delete.pk + 999  # A PK that surely doesn't exist
        # Corrected URL name: 'admin_motorcycle_delete'
        url = reverse('inventory:admin_motorcycle_delete', kwargs={'pk': non_existent_pk})

        response = self.client.post(url, follow=True)

        # get_object_or_404 should raise Http404, which Django handles by returning a 404 response
        self.assertEqual(response.status_code, 404)
        # No success or error message should be set by the view in this case,
        # as it short-circuits with a 404.
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0)


    @mock.patch('inventory.models.Motorcycle.delete')
    def test_delete_motorcycle_as_admin_failure(self, mock_motorcycle_delete):
        """
        Test that an error message is displayed if motorcycle deletion fails.
        """
        # Simulate a database error during deletion
        mock_motorcycle_delete.side_effect = Exception("Database error occurred!")

        self.client.login(username='admin', password='adminpassword')

        # Perform the POST request to delete the motorcycle
        response = self.client.post(self.delete_url, follow=True)

        # Check for redirection back to the management page
        self.assertRedirects(response, reverse('inventory:admin_inventory_management'))

        # Check that the motorcycle still exists
        self.assertTrue(Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists())

        # Check for error message
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertIn('Error deleting motorcycle', str(messages_list[0]))
        self.assertIn('Database error occurred!', str(messages_list[0]))

    def test_delete_motorcycle_as_non_admin(self):
        """
        Test that a non-admin user cannot delete a motorcycle and is redirected
        to the login page.
        """
        self.client.login(username='user', password='userpassword')

        # Ensure the motorcycle exists before deletion attempt
        self.assertTrue(Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists())
        initial_motorcycle_count = Motorcycle.objects.count()

        # Perform the POST request to delete the motorcycle
        response = self.client.post(self.delete_url, follow=True)

        # Check for redirection to the login page (or whatever your AUTH_LOGIN_URL is)
        # Corrected: Redirect to 'users:login'
        self.assertRedirects(response, f'{reverse("users:login")}?next={self.delete_url}')

        # Verify the motorcycle was NOT deleted
        self.assertTrue(Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists())
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count)

        # Check for no success or error messages from the delete view itself
        messages_list = list(messages.get_messages(response.wsgi_request))
        # The AdminRequiredMixin adds a message for insufficient privileges
        self.assertGreater(len(messages_list), 0)
        self.assertIn("You do not have sufficient privileges to access this page.", str(messages_list[0]))


    def test_delete_motorcycle_unauthenticated(self):
        """
        Test that an unauthenticated user cannot delete a motorcycle and is redirected
        to the login page.
        """
        # Ensure the motorcycle exists before deletion attempt
        self.assertTrue(Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists())
        initial_motorcycle_count = Motorcycle.objects.count()

        # Perform the POST request without logging in
        response = self.client.post(self.delete_url, follow=True)

        # Check for redirection to the login page (or whatever your AUTH_LOGIN_URL is)
        # Corrected: Redirect to 'users:login'
        self.assertRedirects(response, f'{reverse("users:login")}?next={self.delete_url}')

        # Verify the motorcycle was NOT deleted
        self.assertTrue(Motorcycle.objects.filter(pk=self.motorcycle_to_delete.pk).exists())
        self.assertEqual(Motorcycle.objects.count(), initial_motorcycle_count)

        # Check for no success or error messages
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 0) # No messages from the delete view
