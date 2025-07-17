from django.test import TestCase, Client
from django.urls import reverse
from django.contrib import messages


from service.models import ServiceProfile
from service.forms import AdminServiceProfileForm
from users.tests.test_helpers.model_factories import UserFactory, SuperUserFactory
from service.tests.test_helpers.model_factories import ServiceProfileFactory


class ServiceProfileCreateUpdateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff_user = UserFactory(
            username="staff_user", is_staff=True, is_superuser=False
        )
        cls.superuser = SuperUserFactory(
            username="superuser"
        )
        cls.regular_user = UserFactory(
            username="regular_user", is_staff=False, is_superuser=False
        )

        cls.existing_profile = ServiceProfileFactory(
            name="Existing Profile for Test", email="existing@example.com"
        )
        cls.existing_profile_user = cls.existing_profile.user

        cls.create_url = reverse("service:admin_create_service_profile")
        cls.update_url = reverse(
            "service:admin_edit_service_profile", kwargs={"pk": cls.existing_profile.pk}
        )

    def setUp(self):
        self.client = Client()

        self.session = self.client.session
        self.session.save()

    def test_view_redirects_anonymous_user(self):
        response = self.client.get(self.create_url)
        self.assertRedirects(
            response, reverse("users:login") + f"?next={self.create_url}"
        )

        response = self.client.get(self.update_url)
        self.assertRedirects(
            response, reverse("users:login") + f"?next={self.update_url}"
        )

    def test_view_denies_access_to_regular_user(self):
        self.client.login(username="regular_user", password="testpassword")
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 302)

    def test_view_allows_access_to_admin_user(self):
        self.client.login(username="adminuser", password="testpassword")

    def test_view_grants_access_to_superuser(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.update_url)
        self.assertEqual(response.status_code, 200)

    def test_get_request_create_new_profile(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.create_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "service/admin_service_profile_create_update.html"
        )
        self.assertIsInstance(response.context["form"], AdminServiceProfileForm)
        self.assertFalse(response.context["is_edit_mode"])
        self.assertIsNone(response.context["current_profile"])

        self.assertFalse(response.context["form"].is_bound)

    def test_get_request_update_existing_profile(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.update_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "service/admin_service_profile_create_update.html"
        )
        self.assertIsInstance(response.context["form"], AdminServiceProfileForm)
        self.assertTrue(response.context["is_edit_mode"])
        self.assertEqual(response.context["current_profile"], self.existing_profile)

        self.assertEqual(response.context["form"].instance, self.existing_profile)

        self.assertFalse(response.context["form"].is_bound)

    def test_get_request_update_non_existent_profile(self):
        self.client.force_login(self.staff_user)
        non_existent_pk = self.existing_profile.pk + 9999
        non_existent_url = reverse(
            "service:admin_edit_service_profile", kwargs={"pk": non_existent_pk}
        )
        response = self.client.get(non_existent_url)
        self.assertEqual(response.status_code, 404)

    def test_post_request_create_new_profile_valid(self):
        self.client.force_login(self.staff_user)
        initial_profile_count = ServiceProfile.objects.count()
        new_user = UserFactory(
            username="new_linked_user", email="new_linked@example.com"
        )

        data = {
            "user": new_user.pk,
            "name": "New Valid Profile",
            "email": "newvalid@example.com",
            "phone_number": "1234567890",
            "address_line_1": "100 New St",
            "city": "Newville",
            "state": "NV",
            "post_code": "99999",
            "country": "US",
        }
        response = self.client.post(self.create_url, data)

        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count + 1)
        new_profile = ServiceProfile.objects.get(name="New Valid Profile")
        self.assertEqual(new_profile.user, new_user)
        self.assertRedirects(response, reverse("service:admin_service_profiles"))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]),
            f"Service Profile for '{new_profile.name}' created successfully.",
        )
        self.assertEqual(messages_list[0].level, messages.SUCCESS)

    def test_post_request_create_new_profile_invalid(self):
        self.client.force_login(self.staff_user)
        initial_profile_count = ServiceProfile.objects.count()

        data = {
            "user": "",
            "name": "",
            "email": "invalid@example.com",
            "phone_number": "1234567890",
            "address_line_1": "100 New St",
            "city": "Newville",
            "state": "NV",
            "post_code": "99999",
            "country": "US",
        }
        response = self.client.post(self.create_url, data)

        self.assertEqual(ServiceProfile.objects.count(), initial_profile_count)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "service/admin_service_profile_create_update.html"
        )
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("name", response.context["form"].errors)

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Please correct the errors below.")
        self.assertEqual(messages_list[0].level, messages.ERROR)

    def test_post_request_update_existing_profile_valid(self):
        self.client.force_login(self.staff_user)
        original_name = self.existing_profile.name
        updated_name = "Updated Existing Profile Name"

        data = {
            "user": self.existing_profile_user.pk if self.existing_profile_user else "",
            "name": updated_name,
            "email": "updated_existing@example.com",
            "phone_number": self.existing_profile.phone_number,
            "address_line_1": self.existing_profile.address_line_1,
            "city": self.existing_profile.city,
            "state": self.existing_profile.state,
            "post_code": self.existing_profile.post_code,
            "country": self.existing_profile.country,
        }
        response = self.client.post(self.update_url, data)

        self.existing_profile.refresh_from_db()
        self.assertEqual(self.existing_profile.name, updated_name)
        self.assertRedirects(response, reverse("service:admin_service_profiles"))

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(
            str(messages_list[0]),
            f"Service Profile for '{self.existing_profile.name}' updated successfully.",
        )
        self.assertEqual(messages_list[0].level, messages.SUCCESS)

    def test_post_request_update_existing_profile_invalid(self):
        self.client.force_login(self.staff_user)
        original_name = self.existing_profile.name

        another_linked_user = ServiceProfileFactory().user

        data = {
            "user": another_linked_user.pk,
            "name": original_name,
            "email": self.existing_profile.email,
            "phone_number": self.existing_profile.phone_number,
            "address_line_1": self.existing_profile.address_line_1,
            "city": self.existing_profile.city,
            "state": self.existing_profile.state,
            "post_code": self.existing_profile.post_code,
            "country": self.existing_profile.country,
        }
        response = self.client.post(self.update_url, data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "service/admin_service_profile_create_update.html"
        )
        self.assertIn("form", response.context)
        self.assertFalse(response.context["form"].is_valid())
        self.assertIn("user", response.context["form"].errors)
        self.assertIn(
            f"This user ({another_linked_user.username}) is already linked to another Service Profile.",
            response.context["form"].errors["user"],
        )

        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(str(messages_list[0]), "Please correct the errors below.")
        self.assertEqual(messages_list[0].level, messages.ERROR)

        self.existing_profile.refresh_from_db()
        self.assertEqual(self.existing_profile.name, original_name)

    def test_post_request_update_non_existent_profile(self):
        self.client.force_login(self.staff_user)
        non_existent_pk = self.existing_profile.pk + 9999
        non_existent_url = reverse(
            "service:admin_edit_service_profile", kwargs={"pk": non_existent_pk}
        )

        data = {
            "name": "Should not matter",
            "email": "shouldnotmatter@example.com",
            "phone_number": "1231231234",
            "address_line_1": "100 New St",
            "city": "Newville",
            "state": "NV",
            "post_code": "99999",
            "country": "US",
        }
        response = self.client.post(non_existent_url, data)
        self.assertEqual(response.status_code, 404)
