from django.test import TestCase
from django.urls import reverse

class ReturnsPolicyViewTest(TestCase):
    """
    Tests for the core app's returns policy view.
    """

    def test_returns_policy_view_GET(self):
        """
        Test that the returns policy view renders successfully and uses the correct template.
        """
        response = self.client.get(reverse('core:returns_policy'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/information/returns_policy.html')
        self.assertContains(response, '<title>Returns Policy - Scooter Shop</title>')
        self.assertContains(response, '<h1>Returns Policy</h1>')

    def test_returns_policy_view_POST_not_allowed(self):
        """
        Test that POST requests to the returns policy view are not allowed.
        """
        response = self.client.post(reverse('core:returns'))
        self.assertEqual(response.status_code, 405) # Method Not Allowed
