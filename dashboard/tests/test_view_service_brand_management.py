from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages
from dashboard.models import ServiceBrand
import io
from PIL import Image

User = get_user_model()


class ServiceBrandManagementViewTest(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='password123',
            is_staff=True
        )

        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='password123'
        )

        image_file = io.BytesIO()
        Image.new('RGB', (10, 10), color = 'red').save(image_file, 'JPEG')
        image_file.seek(0)

        self.test_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=image_file.read(),
            content_type='image/jpeg'
        )

        self.brand1 = ServiceBrand.objects.create(
            name='Brand One',
            is_primary=True,
            image=self.test_image
        )

        self.brand2 = ServiceBrand.objects.create(
            name='Brand Two',
            is_primary=False
        )

        self.client = Client()

        self.management_url = reverse('dashboard:service_brands_management')


    def test_view_requires_login(self):
        response = self.client.get(self.management_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response.url)


    def test_view_requires_staff_access(self):
        self.client.login(username='regularuser', password='password123')
        response = self.client.get(self.management_url)

        self.assertEqual(response.status_code, 302)


    def test_get_management_view_as_staff(self):
        self.client.login(username='staffuser', password='password123')
        response = self.client.get(self.management_url)

        self.assertEqual(response.status_code, 200)

        self.assertIn('form', response.context)
        self.assertIn('service_brands', response.context)
        self.assertIn('primary_brands_count', response.context)
        self.assertEqual(response.context['primary_brands_count'], 1)

        self.assertTemplateUsed(response, 'dashboard/service_brands_management.html')

    def test_add_brand(self):
        self.client.login(username='staffuser', password='password123')

        form_data = {
            'name': 'New Test Brand',
            'is_primary': False,
            'add_brand_submit': 'Add'
        }

        response = self.client.post(self.management_url, form_data)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(ServiceBrand.objects.filter(name='New Test Brand').exists())

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("added successfully" in str(msg) for msg in messages))

    def test_add_primary_brand_with_image(self):
        self.client.login(username='staffuser', password='password123')

        image_file = io.BytesIO()
        Image.new('RGB', (100, 100), color='blue').save(image_file, 'JPEG')
        image_file.seek(0)

        form_data = {
            'name': 'New Primary Brand',
            'is_primary': 'on',
            'add_brand_submit': 'Add',
            'image': SimpleUploadedFile(
                'test_image.jpg',
                image_file.read(),
                content_type='image/jpeg'
            )
        }

        response = self.client.post(self.management_url, form_data)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(ServiceBrand.objects.filter(name='New Primary Brand').exists())

        brand = ServiceBrand.objects.get(name='New Primary Brand')
        self.assertTrue(brand.is_primary)
        self.assertTrue(brand.image)

    def test_add_primary_brand_without_image_fails(self):
        self.client.login(username='staffuser', password='password123')

        form_data = {
            'name': 'Invalid Primary Brand',
            'is_primary': True,
            'add_brand_submit': 'Add'
        }

        response = self.client.post(self.management_url, form_data)

        self.assertEqual(response.status_code, 200)

        self.assertFalse(ServiceBrand.objects.filter(name='Invalid Primary Brand').exists())

        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)


    def test_edit_brand(self):
        self.client.login(username='staffuser', password='password123')

        edit_form_data = {
            'name': 'Updated Brand Name',
            'is_primary': False,
            'brand_id': self.brand2.pk,
            'add_brand_submit': 'Update'
        }

        response = self.client.post(self.management_url, edit_form_data)

        self.assertEqual(response.status_code, 302)

        self.brand2.refresh_from_db()
        self.assertEqual(self.brand2.name, 'Updated Brand Name')
        self.assertFalse(self.brand2.is_primary)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("updated successfully" in str(msg) for msg in messages))

    def test_delete_brand(self):
        self.client.login(username='staffuser', password='password123')

        delete_data = {
            'delete_brand_pk': self.brand2.pk,
        }

        response = self.client.post(self.management_url, delete_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:service_brands_management'))

        self.assertFalse(ServiceBrand.objects.filter(pk=self.brand2.pk).exists())

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("deleted successfully" in str(msg) for msg in messages))


class DeleteServiceBrandViewTest(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='password123',
            is_staff=True
        )

        self.brand = ServiceBrand.objects.create(
            name='Brand To Delete',
            is_primary=False
        )

        self.client = Client()

        self.delete_url = reverse('dashboard:delete_service_brand', args=[self.brand.pk])

    def test_delete_view_requires_login(self):
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response.url)


    def test_delete_view_requires_staff_access(self):
        self.client.login(username='regularuser', password='password123')
        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 302)


    def test_delete_view_requires_post(self):
        self.client.login(username='staffuser', password='password123')

        response = self.client.get(self.delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:service_brands_management'))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invalid request method" in str(msg) for msg in messages))

        self.assertTrue(ServiceBrand.objects.filter(pk=self.brand.pk).exists())

    def test_delete_brand_via_separate_view(self):
        self.client.login(username='staffuser', password='password123')

        response = self.client.post(self.delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:service_brands_management'))

        self.assertFalse(ServiceBrand.objects.filter(pk=self.brand.pk).exists())

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("deleted successfully" in str(msg) for msg in messages))

    def test_delete_nonexistent_brand(self):
        self.client.login(username='staffuser', password='password123')

        non_existent_pk = 9999
        non_existent_url = reverse('dashboard:delete_service_brand', args=[non_existent_pk])

        response = self.client.post(non_existent_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:service_brands_management'))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Error deleting service brand:" in str(msg) for msg in messages))
