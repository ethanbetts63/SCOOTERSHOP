from django.test import TestCase
from django.urls import reverse

class TermsOfUseViewTest(TestCase):
    """
    Tests for the core app's terms of use view.
    """

    def test_terms_of_use_view_GET(self):
        """
        Test that the terms of use view renders successfully and uses the correct template.
        """
        response = self.client.get(reverse('core:terms_of_use'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/information/terms_of_use.html')
        self.assertContains(response, '<title>Terms of Use - Scooter Shop</title>')
        self.assertContains(response, '<h1>Terms of Use</h1>')

    def test_terms_of_use_view_POST_not_allowed(self):
        """
        Test that POST requests to the terms of use view are not allowed.
        """
        response = self.client.post(reverse('core:terms'))
        self.assertEqual(response.status_code, 405) # Method Not Allowed
