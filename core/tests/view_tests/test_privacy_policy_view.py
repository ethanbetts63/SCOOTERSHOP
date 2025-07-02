from django.test import TestCase
from django.urls import reverse

class PrivacyPolicyViewTest(TestCase):
    """
    Tests for the core app's privacy policy view.
    """

    def test_privacy_policy_view_GET(self):
        """
        Test that the privacy policy view renders successfully and uses the correct template.
        """
        response = self.client.get(reverse('core:privacy_policy'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/information/privacy_policy.html')
        self.assertContains(response, '<title>Privacy Policy - Scooter Shop</title>')
        self.assertContains(response, '<h1>Privacy Policy</h1>')

    def test_privacy_policy_view_POST_not_allowed(self):
        """
        Test that POST requests to the privacy policy view are not allowed.
        """
        response = self.client.post(reverse('core:privacy'))
        self.assertEqual(response.status_code, 405) # Method Not Allowed
