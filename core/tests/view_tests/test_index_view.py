from django.test import TestCase
from django.urls import reverse

class IndexViewTest(TestCase):
    """
    Tests for the core app's index view.
    """

    def test_index_view_GET(self):
        """
        Test that the index view renders successfully and uses the correct template.
        """
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/index.html')
        self.assertContains(response, '<title>Scootershop Australia</title>')
        self.assertContains(response, '<h1>Welcome to Scooter Shop</h1>')

    def test_index_view_POST_not_allowed(self):
        """
        Test that POST requests to the index view are not allowed.
        """
        response = self.client.post(reverse('core:index'))
        self.assertEqual(response.status_code, 405) # Method Not Allowed
