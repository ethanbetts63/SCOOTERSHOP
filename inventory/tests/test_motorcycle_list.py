# inventory/tests/test_motorcycle_list.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone # Use timezone.now() for datetimes
import datetime # For date calculations
from decimal import Decimal
from django.contrib.messages import get_messages # Import get_messages

# Import models and views
from inventory.models import Motorcycle, MotorcycleCondition
# Import all list views and function wrappers
from inventory.views.motorcycle_list import (
    MotorcycleListView,
    NewMotorcycleListView,
    UsedMotorcycleListView,
    HireMotorcycleListView,
    AllMotorcycleListView,
    new,
    used,
    hire,
)

# Import HireBooking if testing hire date availability filtering
from hire.models import HireBooking # Uncomment if you need to test HireBooking interaction
from unittest.mock import patch, MagicMock # For mocking if needed
from decimal import Decimal # For price fields

User = get_user_model()

class MotorcycleListViewTests(TestCase):
    def setUp(self):
        # Set up test data for list view tests.
        self.client = Client()

        # Create necessary MotorcycleCondition objects
        self.new_condition = MotorcycleCondition.objects.create(name='new', display_name='New')
        self.used_condition = MotorcycleCondition.objects.create(name='used', display_name='Used')
        self.hire_condition = MotorcycleCondition.objects.create(name='hire', display_name='For Hire')
        self.demo_condition = MotorcycleCondition.objects.create(name='demo', display_name='Demonstration')

        # Create test motorcycles
        self.motorcycle_new = Motorcycle.objects.create(
            title='2024 Yamaha R7', brand='Yamaha', model='R7', year=2024,
            price=Decimal('9000.00'), engine_size='700cc', seats=2, transmission='manual',
            description='Brand new sport bike.', is_available=True,
            date_posted=timezone.now() - datetime.timedelta(days=10) # Posted recently
        )
        self.motorcycle_new.conditions.add(self.new_condition)

        self.motorcycle_used_1 = Motorcycle.objects.create(
            title='2018 Honda CB300R', brand='Honda', model='CB300R', year=2018,
            price=Decimal('4500.00'), odometer=10000, engine_size='300cc', seats=1,
            transmission='manual', description='Used commuter bike.', is_available=True,
            date_posted=timezone.now() - datetime.timedelta(days=30) # Posted earlier
        )
        self.motorcycle_used_1.conditions.add(self.used_condition)

        self.motorcycle_used_2 = Motorcycle.objects.create(
            title='2020 Kawasaki Ninja 650', brand='Kawasaki', model='Ninja 650', year=2020,
            price=Decimal('6000.00'), odometer=8000, engine_size='650cc', seats=2,
            transmission='manual', description='Used sport tourer.', is_available=True,
            date_posted=timezone.now() - datetime.timedelta(days=20) # Posted between
        )
        self.motorcycle_used_2.conditions.add(self.used_condition)

        self.motorcycle_hire = Motorcycle.objects.create(
            title='2021 Vespa GTS 300', brand='Vespa', model='GTS 300', year=2021,
            engine_size='300cc', seats=2, transmission='automatic',
            description='Scooter for hire.', is_available=True,
            daily_hire_rate=Decimal('80.00'), weekly_hire_rate=Decimal('380.00'),
            date_posted=timezone.now() - datetime.timedelta(days=5)
        )
        self.motorcycle_hire.conditions.add(self.hire_condition)

        self.motorcycle_demo = Motorcycle.objects.create(
            title='2023 Suzuki GSX-S1000', brand='Suzuki', model='GSX-S1000', year=2023,
            price=Decimal('11000.00'), odometer=500, engine_size='1000cc', seats=2,
            transmission='manual', description='Demo superbike.', is_available=True,
            date_posted=timezone.now() - datetime.timedelta(days=15)
        )
        self.motorcycle_demo.conditions.add(self.demo_condition)

        self.motorcycle_unavailable = Motorcycle.objects.create(
            title='2015 Harley-Davidson Iron 883', brand='Harley-Davidson', model='Iron 883', year=2015,
            price=Decimal('7000.00'), engine_size='883cc', seats=1, transmission='manual',
            description='Not currently available.', is_available=False,
            date_posted=timezone.now() - datetime.timedelta(days=50)
        )
        self.motorcycle_unavailable.conditions.add(self.used_condition)

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
        url = reverse('inventory:hire')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/hire.html')

    # Test that the main list view only shows available motorcycles.
    def test_motorcycle_list_view_shows_available_motorcycles_to_admin(self):
        # Create an admin user and log them in
        admin_user = User.objects.create_user(
            username='admin', 
            email='admin@example.com', 
            password='password'
        )
        admin_user.is_staff = True
        admin_user.save()
        self.client.login(username='admin', password='password')
        
        # Now access the URL as an admin
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        # Should show all available motorcycles
        self.assertEqual(motorcycles_in_context.count(), 5)
        self.assertIn(self.motorcycle_new, motorcycles_in_context)
        self.assertIn(self.motorcycle_used_1, motorcycles_in_context)
        self.assertIn(self.motorcycle_used_2, motorcycles_in_context)
        self.assertIn(self.motorcycle_hire, motorcycles_in_context)
        self.assertIn(self.motorcycle_demo, motorcycles_in_context) 

        self.assertNotIn(self.motorcycle_unavailable, motorcycles_in_context)
    
    def test_motorcycle_list_view_redirects_non_admin(self):
        # Don't log in as admin
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url)
        # Should redirect (status code 302)
        self.assertEqual(response.status_code, 302)

    # Test that the new list view renders the correct template.
    def test_new_list_view_renders_correct_template(self):
        url = reverse('inventory:new')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/new.html')

    # Test that the new list view only shows motorcycles with 'new' condition.
    def test_new_list_view_filters_by_new_condition(self):
        url = reverse('inventory:new')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        self.assertEqual(motorcycles_in_context.count(), 1)
        self.assertIn(self.motorcycle_new, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_used_1, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_hire, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_demo, motorcycles_in_context)


    # Test that the used list view renders the correct template.
    def test_used_list_view_renders_correct_template(self):
        url = reverse('inventory:used')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/used.html')

    # Test that the used list view shows motorcycles with 'used' or 'demo' condition.
    def test_used_list_view_filters_by_used_or_demo_condition(self):
        url = reverse('inventory:used')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        self.assertEqual(motorcycles_in_context.count(), 3)
        self.assertIn(self.motorcycle_used_1, motorcycles_in_context)
        self.assertIn(self.motorcycle_used_2, motorcycles_in_context)
        self.assertIn(self.motorcycle_demo, motorcycles_in_context) # Demo should be included
        self.assertNotIn(self.motorcycle_new, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_hire, motorcycles_in_context)


    # Test that the hire list view renders the correct template.
    def test_hire_list_view_renders_correct_template(self):
        url = reverse('inventory:hire')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/hire.html')

    # Test that the hire list view only shows motorcycles with 'hire' condition.
    def test_hire_list_view_filters_by_hire_condition(self):
        url = reverse('inventory:hire')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        self.assertEqual(motorcycles_in_context.count(), 1)
        self.assertIn(self.motorcycle_hire, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_new, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_used_1, motorcycles_in_context)
        self.assertNotIn(self.motorcycle_demo, motorcycles_in_context)


def test_list_view_filters_by_brand(self):
    # Create specific motorcycles for this test
    honda_bike = Motorcycle.objects.create(
        title='Test Honda', brand='Honda', model='CBR', year=2020,
        engine_size='500cc', seats=2, transmission='manual',
        description='A test Honda bike.', is_available=True,
        price=5000.00  # Add price since your view sorts by it
    )
    honda_bike.conditions.add(self.new_condition)  # Add a condition
    
    kawasaki_bike = Motorcycle.objects.create(
        title='Test Kawasaki', brand='Kawasaki', model='Ninja', year=2021,
        engine_size='650cc', seats=2, transmission='manual',
        description='A test Kawasaki bike.', is_available=True,
        price=6000.00
    )
    kawasaki_bike.conditions.add(self.new_condition)
    
    yamaha_bike = Motorcycle.objects.create(
        title='Test Yamaha', brand='Yamaha', model='MT-07', year=2022,
        engine_size='700cc', seats=2, transmission='manual',
        description='A test Yamaha bike.', is_available=True,
        price=7000.00
    )
    yamaha_bike.conditions.add(self.new_condition)
    
    # Make sure all bikes are saved with their conditions
    honda_bike.save()
    kawasaki_bike.save()
    yamaha_bike.save()

    url = reverse('inventory:motorcycle-list')

    # Test filtering by Honda
    response = self.client.get(f"{url}?brand=Honda")
    self.assertEqual(response.status_code, 200)
    motorcycles_in_context = list(response.context['motorcycles'])
    self.assertEqual(len(motorcycles_in_context), 1)
    self.assertIn(honda_bike, motorcycles_in_context)

    # Test filtering by Kawasaki
    response = self.client.get(f"{url}?brand=Kawasaki")
    self.assertEqual(response.status_code, 200)
    motorcycles_in_context = list(response.context['motorcycles'])
    self.assertEqual(len(motorcycles_in_context), 1)
    self.assertIn(kawasaki_bike, motorcycles_in_context)

    # Test case insensitive filtering
    response = self.client.get(f"{url}?brand=honda")  
    self.assertEqual(response.status_code, 200)
    motorcycles_in_context = list(response.context['motorcycles'])
    self.assertEqual(len(motorcycles_in_context), 1)
    self.assertIn(honda_bike, motorcycles_in_context)

    # Test filtering by a brand with no matches
    response = self.client.get(f"{url}?brand=Suzuki")
    self.assertEqual(response.status_code, 200)
    motorcycles_in_context = list(response.context['motorcycles'])
    self.assertEqual(len(motorcycles_in_context), 0)


    # Test filtering by model.
    def test_list_view_filters_by_model(self):
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url, {'model': 'R7'})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']
        self.assertEqual(motorcycles_in_context.count(), 1)
        self.assertIn(self.motorcycle_new, motorcycles_in_context)


    # Test filtering by year range.
    def test_list_view_filters_by_year_range(self):
        # Create specific motorcycles for this test
        bike_2019 = Motorcycle.objects.create(
            title='Bike 2019', brand='A', model='1', year=2019,
            engine_size='125cc', seats=1, transmission='manual',
            description='2019 bike.', is_available=True
        )
        bike_2020 = Motorcycle.objects.create(
            title='Bike 2020', brand='B', model='2', year=2020,
            engine_size='500cc', seats=2, transmission='manual',
            description='2020 bike.', is_available=True
        )
        bike_2021 = Motorcycle.objects.create(
            title='Bike 2021', brand='C', model='3', year=2021,
            engine_size='600cc', seats=2, transmission='manual',
            description='2021 bike.', is_available=True
        )
        bike_2022 = Motorcycle.objects.create(
            title='Bike 2022', brand='D', model='4', year=2022,
            engine_size='1000cc', seats=2, transmission='manual',
            description='2022 bike.', is_available=True
        )

        url = reverse('inventory:motorcycle-list')

        # Test filtering between 2020 and 2022
        response = self.client.get(url, {'year_min': 2020, 'year_max': 2022})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        self.assertEqual(len(motorcycles_in_context), 3) # Expected: 2020, 2021, 2022
        self.assertIn(bike_2020, motorcycles_in_context)
        self.assertIn(bike_2021, motorcycles_in_context)
        self.assertIn(bike_2022, motorcycles_in_context)
        self.assertNotIn(bike_2019, motorcycles_in_context)

        # Test filtering with only year_min
        response = self.client.get(url, {'year_min': 2021})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        # Expected: 2021, 2022
        self.assertEqual(len(motorcycles_in_context), 2)
        self.assertIn(bike_2021, motorcycles_in_context)
        self.assertIn(bike_2022, motorcycles_in_context)

        # Test filtering with only year_max
        response = self.client.get(url, {'year_max': 2020})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        # Expected: 2019, 2020
        self.assertEqual(len(motorcycles_in_context), 2)
        self.assertIn(bike_2019, motorcycles_in_context)
        self.assertIn(bike_2020, motorcycles_in_context)

        # Test filtering with no matches
        response = self.client.get(url, {'year_min': 2025})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        self.assertEqual(len(motorcycles_in_context), 0)


    # Test filtering by price range.
    def test_list_view_filters_by_price_range(self):
        # Create specific motorcycles for this test
        cheap_bike = Motorcycle.objects.create(
            title='Cheap Bike', brand='A', model='1', year=2019,
            price=Decimal('3000.00'), engine_size='125cc', seats=1, transmission='manual',
            description='Cheap.', is_available=True
        )
        mid_price_bike_1 = Motorcycle.objects.create(
            title='Mid Price Bike 1', brand='B', model='2', year=2020,
            price=Decimal('6500.00'), engine_size='500cc', seats=2, transmission='manual',
            description='Mid range.', is_available=True
        )
        mid_price_bike_2 = Motorcycle.objects.create(
            title='Mid Price Bike 2', brand='C', model='3', year=2021,
            price=Decimal('7800.00'), engine_size='600cc', seats=2, transmission='manual',
            description='Mid range.', is_available=True
        )
        expensive_bike = Motorcycle.objects.create(
            title='Expensive Bike', brand='D', model='4', year=2022,
            price=Decimal('10000.00'), engine_size='1000cc', seats=2, transmission='manual',
            description='Expensive.', is_available=True
        )
        # Bike with no price
        hire_bike = Motorcycle.objects.create(
            title='Hire Bike', brand='E', model='5', year=2023,
            engine_size='300cc', seats=2, transmission='automatic',
            description='For hire.', is_available=True, daily_hire_rate=Decimal('50.00')
        )


        url = reverse('inventory:motorcycle-list')

        # Test filtering between 6000 and 8000
        response = self.client.get(url, {'price_min': 6000, 'price_max': 8000})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        self.assertEqual(len(motorcycles_in_context), 2)
        self.assertIn(mid_price_bike_1, motorcycles_in_context)
        self.assertIn(mid_price_bike_2, motorcycles_in_context)
        self.assertNotIn(cheap_bike, motorcycles_in_context)
        self.assertNotIn(expensive_bike, motorcycles_in_context)
        self.assertNotIn(hire_bike, motorcycles_in_context) # Should not be included as it has no sale price

        # Test filtering with only price_min
        response = self.client.get(url, {'price_min': 7000})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        # Expected: Mid Price Bike 2 (7800), Expensive Bike (10000)
        self.assertEqual(len(motorcycles_in_context), 2)
        self.assertIn(mid_price_bike_2, motorcycles_in_context)
        self.assertIn(expensive_bike, motorcycles_in_context)

        # Test filtering with only price_max
        response = self.client.get(url, {'price_max': 7000})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        # Expected: Cheap Bike (3000), Mid Price Bike 1 (6500)
        self.assertEqual(len(motorcycles_in_context), 2)
        self.assertIn(cheap_bike, motorcycles_in_context)
        self.assertIn(mid_price_bike_1, motorcycles_in_context)

        # Test filtering with no matches
        response = self.client.get(url, {'price_min': 15000})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = list(response.context['motorcycles'])
        self.assertEqual(len(motorcycles_in_context), 0)


    # Test sorting by price low to high.
    def test_list_view_sorts_by_price_low_to_high(self):
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url, {'order': 'price_low_to_high'})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        # Get prices of available bikes that have a price
        priced_bikes = [b for b in motorcycles_in_context if b.price is not None]
        # Check if prices are in ascending order
        prices = [b.price for b in priced_bikes]
        self.assertEqual(prices, sorted(prices))


    # Test sorting by price high to low.
    def test_list_view_sorts_by_price_high_to_low(self):
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url, {'order': 'price_high_to_low'})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        priced_bikes = [b for b in motorcycles_in_context if b.price is not None]
        prices = [b.price for b in priced_bikes]
        self.assertEqual(prices, sorted(prices, reverse=True))


    # Test sorting by age new to old (year descending).
    def test_list_view_sorts_by_age_new_to_old(self):
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url, {'order': 'age_new_to_old'})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        # Get years of available bikes
        years = [b.year for b in motorcycles_in_context]
        self.assertEqual(years, sorted(years, reverse=True))


    # Test sorting by age old to new (year ascending).
    def test_list_view_sorts_by_age_old_to_new(self):
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url, {'order': 'age_old_to_new'})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']

        # Get years of available bikes
        years = [b.year for b in motorcycles_in_context]
        self.assertEqual(years, sorted(years))

    # Test that brand and year options are included in context.
    def test_list_view_includes_filter_options_in_context(self):
        url = reverse('inventory:motorcycle-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('brands', response.context)
        self.assertIn('years', response.context)

        # Check some expected brands are present
        expected_brands = ['Honda', 'Kawasaki', 'Suzuki', 'Vespa', 'Yamaha'] # Add other brands from your setup
        for brand in expected_brands:
             self.assertIn(brand, response.context['brands'])

        # Check the year range is correctly generated (max year to min year)
        min_year = min([b.year for b in Motorcycle.objects.filter(is_available=True)])
        max_year = max([b.year for b in Motorcycle.objects.filter(is_available=True)])
        expected_years = list(range(max_year, min_year - 1, -1))
        self.assertEqual(response.context['years'], expected_years)


    # Test filtering by daily hire rate range.
    def test_hire_list_view_filters_by_daily_rate_range(self):
        hire_url = reverse('inventory:hire')

        # Create another hire bike with a different rate
        motorcycle_hire_cheap = Motorcycle.objects.create(
            title='Cheap Hire Bike', brand='Cheap', model='Hire', year=2020,
            engine_size='125cc', seats=1, transmission='automatic',
            description='Affordable hire scooter.', is_available=True,
            daily_hire_rate=Decimal('50.00'),
            date_posted=timezone.now()
        )
        motorcycle_hire_cheap.conditions.add(self.hire_condition)


        response = self.client.get(hire_url, {'daily_rate_min': 60, 'daily_rate_max': 90})
        self.assertEqual(response.status_code, 200)
        motorcycles_in_context = response.context['motorcycles']
        self.assertEqual(motorcycles_in_context.count(), 1)
        self.assertIn(self.motorcycle_hire, motorcycles_in_context) # Rate 80.00
        self.assertNotIn(motorcycle_hire_cheap, motorcycles_in_context) # Rate 50.00


    # Test that selected date range is included in the context.
    def test_hire_list_view_includes_date_range_in_context(self):
        hire_url = reverse('inventory:hire')
        start_date_str = '2025-07-01'
        end_date_str = '2025-07-10'
        response = self.client.get(hire_url, {'hire_start_date': start_date_str, 'hire_end_date': end_date_str})
        self.assertEqual(response.status_code, 200)
        self.assertIn('hire_start_date', response.context)
        self.assertIn('hire_end_date', response.context)
        self.assertIn('hire_days', response.context)

        self.assertEqual(response.context['hire_start_date'], start_date_str)
        self.assertEqual(response.context['hire_end_date'], end_date_str)
        # Calculate expected days: 10 - 1 + 1 = 10 days
        self.assertEqual(response.context['hire_days'], 10)

        # Add check for messages - expect no error messages for valid dates
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 0, f"Expected no messages, but found: {[str(m) for m in messages]}")


    # Test that the 'new' function view calls NewMotorcycleListView.as_view().
    def test_new_function_view_calls_class_based_view(self):
        # This is a basic check, you might mock NewMotorcycleListView.as_view() for a stricter test
        url = reverse('inventory:new')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200) # Should return 200 like the CBV

    # Test that the 'used' function view calls UsedMotorcycleListView.as_view().
    def test_used_function_view_calls_class_based_view(self):
        url = reverse('inventory:used')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200) # Should return 200 like the CBV

    # Test that the 'hire' function view calls HireMotorcycleListView.as_view().
    def test_hire_function_view_calls_class_based_view(self):
        url = reverse('inventory:hire')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200) # Should return 200 like the CBV


    # Add tests for pagination if you have more than paginate_by motorcycles
    # # Test pagination on the list view.
    # def test_pagination(self):
    #     # Create enough motorcycles to trigger pagination (more than paginate_by)
    #     for i in range(MotorcycleListView.paginate_by + 5):
    #          Motorcycle.objects.create(...) # Create unique motorcycles
    #
    #     url = reverse('inventory:motorcycle-list')
    #     response = self.client.get(url)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertTrue('is_paginated' in response.context)
    #     self.assertEqual(response.context['paginator'].count, total_number_of_bikes) # Check total count
    #     self.assertEqual(response.context['page_obj'].number, 1) # Check current page
    #     self.assertEqual(len(response.context['motorcycles']), MotorcycleListView.paginate_by) # Check items per page
    #
    #     # Test the second page
    #     response_page2 = self.client.get(url, {'page': 2})
    #     self.assertEqual(response_page2.status_code, 200)
    #     self.assertEqual(response_page2.context['page_obj'].number, 2)