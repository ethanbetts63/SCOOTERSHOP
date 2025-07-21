
from django.test import TestCase, Client
from django.urls import reverse
from users.tests.test_helpers.model_factories import UserFactory
from dashboard.models import Review

class ReviewAddViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory(is_staff=True)
        self.client.force_login(self.user)
        self.url = reverse('dashboard:review_create')

    def test_get_review_add_view(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/review_create_update.html')

    def test_add_review(self):
        data = {
            'author_name': 'John Doe',
            'rating': 5,
            'text': 'This is a great scooter shop!',
            'is_active': 'on',
            'display_order': 1,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Review.objects.filter(author_name='John Doe').exists())
