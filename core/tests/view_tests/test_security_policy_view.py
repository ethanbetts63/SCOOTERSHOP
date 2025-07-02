from django.test import TestCase
from django.urls import reverse

class SecurityPolicyViewTest(TestCase):
    """
    Tests for the core app's security policy view.
    """

    def test_security_policy_view_GET(self):
        """
        Test that the security policy view renders successfully and uses the correct template.
        """
        response = self.client.get(reverse('core:security_policy'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/information/security_policy.html')
        self.assertContains(response, '<title>Security Policy - Scooter Shop</title>')
        self.assertContains(response, '<h1>Security Policy</h1>')

    def test_security_policy_view_POST_not_allowed(self):
        """
        Test that POST requests to the security policy view are not allowed.
        """
        response = self.client.post(reverse('core:security'))
        self.assertEqual(response.status_code, 405) # Method Not Allowed
