# inventory/tests/test_motorcycle_list.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime
from decimal import Decimal
from django.contrib.messages import get_messages

# Import models and views
from inventory.models import Motorcycle, MotorcycleCondition
from inventory.views.motorcycle_list import (
    MotorcycleListView,
    NewMotorcycleListView,
    UsedMotorcycleListView,
    HireMotorcycleListView,
    AllMotorcycleListView,
)

# Import HireBooking if testing hire date availability filtering
from .hire_booking import HireBooking

User = get_user_model()

class MotorcycleListViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create admin/staff user
        self.staff_user = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='password'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()

        # Create motorcycle conditions
        self.new_condition = MotorcycleCondition.objects.create(name='new', display_name='New')
        self.used_condition = MotorcycleCondition.objects.create(name='used', display_name='Used')
        self.hire_condition = MotorcycleCondition.objects.create(name='hire', display_name='For Hire')
        self.demo_condition = MotorcycleCondition.objects.create(name='demo', display_name='Demonstration')

        # Create base set of motorcycles used by all tests
        # 1. New motorcycle
        self.motorcycle_new = Motorcycle.objects.create(
            title='2024 Yamaha R7', brand='Yamaha', model='R7', year=2024,
            price=Decimal('9000.00'), engine_size='700cc', seats=2, transmission='manual',
            description='Brand new sport bike.', is_available=True,
            date_posted=timezone.now() - datetime.timedelta(days=10)
        )
        self.motorcycle_new.conditions.add(self.new_condition)

        # 2. Used motorcycles
        self.motorcycle_used_1 = Motorcycle.objects.create(
            title='2018 Honda CB300R', brand='Honda', model='CB300R', year=2018,
            price=Decimal('4500.00'), odometer=10000, engine_size='300cc', seats=1,
            transmission='manual', description='Used commuter bike.', is_available=True,
            date_posted=timezone.now() - datetime.timedelta(days=30)
        )
        self.motorcycle_used_1.conditions.add(self.used_condition)

        self.motorcycle_used_2 = Motorcycle.objects.create(
            title='2020 Kawasaki Ninja 650', brand='Kawasaki', model='Ninja 650', year=2020,
            price=Decimal('6000.00'), odometer=8000, engine_size='650cc', seats=2,
            transmission='manual', description='Used sport tourer.', is_available=True,
            date_posted=timezone.now() - datetime.timedelta(days=20)
        )
        self.motorcycle_used_2.conditions.add(self.used_condition)

        # 3. Demo motorcycle
        self.motorcycle_demo = Motorcycle.objects.create(
            title='2023 Suzuki GSX-S1000', brand='Suzuki', model='GSX-S1000', year=2023,
            price=Decimal('11000.00'), odometer=500, engine_size='1000cc', seats=2,
            transmission='manual', description='Demo superbike.', is_available=True,
            date_posted=timezone.now() - datetime.timedelta(days=15)
        )
        self.motorcycle_demo.conditions.add(self.demo_condition)

        # 4. Hire motorcycle
        self.motorcycle_hire = Motorcycle.objects.create(
            title='2021 Vespa GTS 300', brand='Vespa', model='GTS 300', year=2021,
            engine_size='300cc', seats=2, transmission='automatic',
            description='Scooter for hire.', is_available=True,
            date_posted=timezone.now() - datetime.timedelta(days=5)
        )
        self.motorcycle_hire.conditions.add(self.hire_condition)

        # 5. Hire motorcycle with cheaper rate
        self.motorcycle_hire_cheap = Motorcycle.objects.create(
            title='Cheap Hire Bike', brand='Honda', model='PCX125', year=2020,
            engine_size='125cc', seats=1, transmission='automatic',
            description='Affordable hire scooter.', is_available=True,
            date_posted=timezone.now() - datetime.timedelta(days=8)
        )
        self.motorcycle_hire_cheap.conditions.add(self.hire_condition)

        # 6. Unavailable used motorcycle
        self.motorcycle_unavailable = Motorcycle.objects.create(
            title='2015 Harley-Davidson Iron 883', brand='Harley-Davidson', model='Iron 883', year=2015,
            price=Decimal('7000.00'), engine_size='883cc', seats=1, transmission='manual',
            description='Not currently available.', is_available=False,
            date_posted=timezone.now() - datetime.timedelta(days=50)
        )
        self.motorcycle_unavailable.conditions.add(self.used_condition)

        # 7-10. Motorcycles for price and year range tests
        self.year_bikes = {}
        self.price_bikes = {}

        for i, year in enumerate(range(2019, 2023)):
            bike = Motorcycle.objects.create(
                title=f'Test Year Bike {year}', brand=f'Brand{i}', model=f'Model{i}', year=year,
                price=Decimal(3000 + i * 1000), engine_size=f'{500 + i * 100}cc', seats=2,
                transmission='manual', description=f'{year} test bike.', is_available=True,
                date_posted=timezone.now() - datetime.timedelta(days=i)
            )
            bike.conditions.add(self.new_condition)
            self.year_bikes[year] = bike
            self.price_bikes[3000 + i * 1000] = bike

    # Test templates
    def test_new_motorcycle_list_view_renders_correct_template(self):
        url = reverse('inventory:new')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/new.html')

    def test_used_motorcycle_list_view_renders_correct_template(self):
        url = reverse('inventory:used')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/used.html')

    def test_hire_motorcycle_list_view_renders_correct_template(self):
        url = reverse('hire:step2_choose_bike')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/hire.html')

    # Test admin view permissions
    def test_motorcycle_list_view_shows_available_motorcycles_to_admin(self):
        self.client.login(username=self.staff_user.username, password='password')
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        # Check that it shows ALL motorcycles, including unavailable
        expected_count = Motorcycle.objects.count()
        self.assertEqual(motorcycles_in_context.count(), expected_count)
        self.assertIn(self.motorcycle_unavailable, motorcycles_in_context)

    def test_motorcycle_list_view_redirects_non_admin(self):
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Should redirect

    # Test condition filters
    def test_new_list_view_filters_by_new_condition(self):
        url = reverse('inventory:new')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        # Should only show motorcycles with new condition
        expected_bikes = [self.motorcycle_new] + list(self.year_bikes.values())
        self.assertEqual(motorcycles_in_context.count(), len(expected_bikes))
        for bike in expected_bikes:
            self.assertIn(bike, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_used_1, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_hire, motorcycles_in_context)

    def test_used_list_view_filters_by_used_or_demo_condition(self):
        url = reverse('inventory:used')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        # Should show motorcycles with used or demo condition
        expected_bikes = [self.motorcycle_used_1, self.motorcycle_used_2, self.motorcycle_demo]
        # Should not include unavailable motorcycles to regular users
        self.assertEqual(motorcycles_in_context.count(), len(expected_bikes))
        for bike in expected_bikes:
            self.assertIn(bike, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_new, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_hire, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_unavailable, motorcycles_in_context)

    def test_hire_list_view_filters_by_hire_condition(self):
        url = reverse('hire:step2_choose_bike')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        # Should only show motorcycles with hire condition
        expected_bikes = [self.motorcycle_hire, self.motorcycle_hire_cheap]
        self.assertEqual(motorcycles_in_context.count(), len(expected_bikes))
        for bike in expected_bikes:
            self.assertIn(bike, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_new, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_used_1, motorcycles_in_context)

    # Test filtering by brand
    def test_list_view_filters_by_brand(self):
        self.client.login(username=self.staff_user.username, password='password')
        url = reverse('inventory:motorcycle-list')

        # Test filtering by Honda (should show used Honda and hire Honda)
        response = self.client.get(f"{url}?brand=Honda")
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        expected_honda_bikes = [self.motorcycle_used_1, self.motorcycle_hire_cheap]
        self.assertEqual(len(motorcycles_in_context), len(expected_honda_bikes))
        for bike in expected_honda_bikes:
            self.assertIn(bike, motorcycles_in_context)

        # Test filtering by Kawasaki
        response = self.client.get(f"{url}?brand=Kawasaki")
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        self.assertEqual(len(motorcycles_in_context), 1)
        self.assertIn(self.motorcycle_used_2, motorcycles_in_context)

        # Test case insensitive filtering
        response = self.client.get(f"{url}?brand=yamaha")
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        self.assertEqual(len(motorcycles_in_context), 1)
        self.assertIn(self.motorcycle_new, motorcycles_in_context)

        # Test filtering by a brand with no matches
        response = self.client.get(f"{url}?brand=Ducati")
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        self.assertEqual(len(motorcycles_in_context), 0)

    # Test filtering by model
    def test_list_view_filters_by_model(self):
        self.client.login(username=self.staff_user.username, password='password')
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url, {'model': 'R7'})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']
        self.assertEqual(motorcycles_in_context.count(), 1)
        self.assertIn(self.motorcycle_new, motorcycles_in_context)

    # Test filtering by year range
    def test_list_view_filters_by_year_range(self):
        self.client.login(username=self.staff_user.username, password='password')
        url = reverse('inventory:motorcycle-list')

        # Test filtering between 2020 and 2022
        response = self.client.get(url, {'year_min': 2020, 'year_max': 2022})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        expected_bikes = [
            self.motorcycle_used_2,  # Kawasaki 2020
            self.motorcycle_hire,    # Vespa 2021
            self.motorcycle_hire_cheap,  # Honda PCX 2020
            self.year_bikes[2020],   # Test year bike 2020
            self.year_bikes[2021],   # Test year bike 2021
            self.year_bikes[2022]    # Test year bike 2022
        ]
        self.assertEqual(len(motorcycles_in_context), len(expected_bikes))
        for bike in expected_bikes:
            self.assertIn(bike, motorcycles_in_context)
        self.assertNotIn(self.year_bikes[2019], motorcycles_in_context)
        self.assertNotIn(self.motorcycle_unavailable, motorcycles_in_context)  # 2015

        # Test filtering with only year_min
        response = self.client.get(url, {'year_min': 2023})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        expected_bikes = [self.motorcycle_new, self.motorcycle_demo]  # 2024 Yamaha and 2023 Suzuki
        self.assertEqual(len(motorcycles_in_context), len(expected_bikes))
        for bike in expected_bikes:
            self.assertIn(bike, motorcycles_in_context)

        # Test filtering with only year_max
        response = self.client.get(url, {'year_max': 2019})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        expected_bikes = [self.motorcycle_used_1, self.motorcycle_unavailable, self.year_bikes[2019]]
        self.assertEqual(len(motorcycles_in_context), len(expected_bikes))
        for bike in expected_bikes:
            self.assertIn(bike, motorcycles_in_context)

        # Test filtering by price range
    def test_list_view_filters_by_price_range(self):
        self.client.login(username=self.staff_user.username, password='password')
        url = reverse('inventory:motorcycle-list')

        # Test filtering between 6000 and 8000
        response = self.client.get(url, {'price_min': 6000, 'price_max': 8000})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        expected_bikes = [
            self.motorcycle_used_2,  # Kawasaki at 6000
            self.motorcycle_unavailable,  # Harley at 7000
            self.price_bikes[6000]  # Test price bike at 6000
        ]

        self.assertEqual(len(motorcycles_in_context), len(expected_bikes))
        for bike in expected_bikes:
            self.assertIn(bike, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_new, motorcycles_in_context)  # 9000
        self.assertNotIn(self.motorcycle_used_1, motorcycles_in_context)  # 4500

        # Test filtering with only price_min
        response = self.client.get(url, {'price_min': 9000})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        expected_bikes = [self.motorcycle_new, self.motorcycle_demo]  # 9000 and 11000
        self.assertEqual(len(motorcycles_in_context), len(expected_bikes))
        for bike in expected_bikes:
            self.assertIn(bike, motorcycles_in_context)

        # Test filtering with only price_max - CORRECTED
        response = self.client.get(url, {'price_max': 5000})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        expected_bikes = [self.motorcycle_used_1, self.price_bikes[3000], self.price_bikes[4000], self.price_bikes[5000]]  # 4500, 3000, 4000, 5000
        self.assertEqual(len(motorcycles_in_context), len(expected_bikes))
        for bike in expected_bikes:
            self.assertIn(bike, motorcycles_in_context)

    # Test sorting by price
    def test_list_view_sorts_by_price_low_to_high(self):
        self.client.login(username=self.staff_user.username, password='password')
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url, {'order': 'price_low_to_high'})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        # Get prices of motorcycles that have a price (exclude None)
        priced_bikes = [b for b in motorcycles_in_context if b.price is not None]
        prices = [b.price for b in priced_bikes]
        # Check if prices are in ascending order
        self.assertEqual(prices, sorted(prices))

    def test_list_view_sorts_by_price_high_to_low(self):
        self.client.login(username=self.staff_user.username, password='password')
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url, {'order': 'price_high_to_low'})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        priced_bikes = [b for b in motorcycles_in_context if b.price is not None]
        prices = [b.price for b in priced_bikes]
        self.assertEqual(prices, sorted(prices, reverse=True))

    # Test sorting by age
    def test_list_view_sorts_by_age_new_to_old(self):
        self.client.login(username=self.staff_user.username, password='password')
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url, {'order': 'age_new_to_old'})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        years = [b.year for b in motorcycles_in_context]
        self.assertEqual(years, sorted(years, reverse=True))

    def test_list_view_sorts_by_age_old_to_new(self):
        self.client.login(username=self.staff_user.username, password='password')
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url, {'order': 'age_old_to_new'})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        years = [b.year for b in motorcycles_in_context]
        self.assertEqual(years, sorted(years))

    # Test filter options in context
    def test_list_view_includes_filter_options_in_context(self):
        self.client.login(username=self.staff_user.username, password='password')
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('brands', response.context)
        self.assertIn('years', response.context)

        # Check all expected brands are present
        expected_brands = ['Yamaha', 'Honda', 'Kawasaki', 'Suzuki', 'Vespa', 'Harley-Davidson']
        for brand in expected_brands:
            self.assertIn(brand, response.context['brands'])

        # Check the year range is correctly generated
        min_year = min([b.year for b in Motorcycle.objects.all()])
        max_year = max([b.year for b in Motorcycle.objects.all()])
        expected_years = list(range(max_year, min_year - 1, -1))
        self.assertEqual(response.context['years'], expected_years)

    # Test hire view specific functionality
    def test_hire_list_view_filters_by_daily_rate_range(self):
        hire_url = reverse('hire:step2_choose_bike')
        response = self.client.get(hire_url, {'daily_rate_min': 60, 'daily_rate_max': 90})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']
        self.assertEqual(motorcycles_in_context.count(), 1)
        self.assertIn(self.motorcycle_hire, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_hire_cheap, motorcycles_in_context)

    def test_hire_list_view_includes_date_range_in_context(self):
        hire_url = reverse('hire:step2_choose_bike')
        start_date_str = '2025-07-01'
        end_date_str = '2025-07-10'
        response = self.client.get(hire_url, {'hire_start_date': start_date_str, 'hire_end_date': end_date_str})
        self.assertEqual(response.status_code, 200)
        self.assertIn('hire_start_date', response.context)
        self.assertIn('hire_end_date', response.context)
        self.assertIn('hire_days', response.context)

        self.assertEqual(response.context['hire_start_date'], start_date_str)
        self.assertEqual(response.context['hire_end_date'], end_date_str)
        self.assertEqual(response.context['hire_days'], 10)

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 0, f"Expected no messages, but found: {[str(m) for m in messages]}")