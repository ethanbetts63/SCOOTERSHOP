from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse("users:register")
        self.login_url = reverse("users:login")
        self.logout_url = reverse("users:logout")
        self.index_url = reverse("core:index")

        # Create a test user
        self.user = User.objects.create_user(
            username="testuser", password="testpassword"
        )

    def test_register_view_get(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/register.html")

    def test_register_view_post(self):
        response = self.client.post(
            self.register_url,
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "newpassword",
                "confirmation": "newpassword",
            },
        )
        self.assertRedirects(response, self.index_url)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_login_view_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/login.html")

    def test_login_view_post_successful(self):
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "testpassword"}
        )
        self.assertRedirects(response, self.index_url)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_view_post_unsuccessful(self):
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/login.html")
        self.assertContains(response, "Invalid username and/or password.")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_view(self):
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.index_url)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
