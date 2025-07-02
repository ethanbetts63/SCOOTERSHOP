from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
import datetime
from inventory.models import Motorcycle
from ...test_helpers.model_factories import MotorcycleFactory, MotorcycleConditionFactory

class MotorcycleListViewTest(TestCase):
    

    @classmethod
    def setUpTestData(cls):
        
        cls.client = Client()

                                                                             
        cls.condition_new = MotorcycleConditionFactory(name='new', display_name='New')
        cls.condition_used = MotorcycleConditionFactory(name='used', display_name='Used')
        cls.condition_demo = MotorcycleConditionFactory(name='demo', display_name='Demo')
                                                                                        
        base_time_setup = datetime.datetime(2023, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        delta_seconds = 0

                                                                  
        def create_and_set_date(brand, model, year, price, engine_size, conditions):
            nonlocal delta_seconds
            moto = MotorcycleFactory(
                brand=brand,
                model=model,
                year=year,
                price=price,
                engine_size=engine_size,
                conditions=conditions,
                is_available=True,                               
            )
            moto.date_posted = base_time_setup + datetime.timedelta(seconds=delta_seconds)
            moto.save()
            delta_seconds += 1
            return moto

                                                                                  
                                                                                            
        create_and_set_date('Honda', 'CBR1000RR', 2023, Decimal('15000.00'), 1000, [cls.condition_new.name])
        create_and_set_date('Yamaha', 'YZF-R6', 2022, Decimal('12000.00'), 600, [cls.condition_new.name])
        create_and_set_date('Suzuki', 'GSX-R750', 2023, Decimal('13000.00'), 750, [cls.condition_new.name])

        create_and_set_date('Honda', 'CRF250L', 2020, Decimal('8000.00'), 250, [cls.condition_used.name])
        create_and_set_date('Kawasaki', 'Ninja 400', 2019, Decimal('7000.00'), 400, [cls.condition_used.name])
        create_and_set_date('Yamaha', 'MT-07', 2021, Decimal('9500.00'), 700, [cls.condition_demo.name])
        create_and_set_date('Ducati', 'Monster 821', 2021, Decimal('11000.00'), 800, [cls.condition_demo.name])
        create_and_set_date('KTM', 'Duke 390', 2022, Decimal('6000.00'), 390, [cls.condition_used.name])

                                                                                     
        for i in range(1, 15):
            create_and_set_date(
                brand=f'PaginatedBrand{i}',
                model=f'PModel{i}',
                year=2020,
                price=Decimal(f'{5000 + i*100}.00'),
                engine_size=500,
                conditions=[cls.condition_used.name]
            )

    def test_all_motorcycles_page_renders_empty_initially(self):
        
        response = self.client.get(reverse('inventory:all'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycle_list.html')

                            
        self.assertIn('motorcycles', response.context)
        self.assertIn('page_obj', response.context)
        self.assertIn('unique_makes', response.context)
        self.assertIn('current_condition_slug', response.context)
        self.assertIn('page_title', response.context)
        self.assertIn('years', response.context)

                                                                                  
        page_obj = response.context['page_obj']
        self.assertEqual(len(response.context['motorcycles']), 0)
        self.assertFalse(page_obj.object_list)                              

                                                            
        expected_all_makes = set(Motorcycle.objects.values_list('brand', flat=True).distinct())
        self.assertEqual(set(response.context['unique_makes']), expected_all_makes)

                                        
        self.assertEqual(response.context['current_condition_slug'], 'all')
        self.assertEqual(response.context['page_title'], 'All Motorcycles')
        self.assertIsInstance(response.context['years'], list)
        self.assertGreater(len(response.context['years']), 0)
        self.assertContains(response, 'No motorcycles match the current criteria.')


    def test_new_motorcycles_page_renders_empty_initially(self):
        
        response = self.client.get(reverse('inventory:new'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycle_list.html')

        page_obj = response.context['page_obj']
        self.assertEqual(len(response.context['motorcycles']), 0)
        self.assertFalse(page_obj.object_list)

                                                                                
        expected_new_makes = set(Motorcycle.objects.filter(conditions__name='new').values_list('brand', flat=True).distinct())
        self.assertEqual(set(response.context['unique_makes']), expected_new_makes)

        self.assertEqual(response.context['current_condition_slug'], 'new')
        self.assertEqual(response.context['page_title'], 'New Motorcycles')
        self.assertContains(response, 'No motorcycles match the current criteria.')


    def test_used_motorcycles_page_renders_empty_initially(self):
        
        response = self.client.get(reverse('inventory:used'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/motorcycle_list.html')

        page_obj = response.context['page_obj']
        self.assertEqual(len(response.context['motorcycles']), 0)
        self.assertFalse(page_obj.object_list)

                                                                                      
        expected_used_makes = set(Motorcycle.objects.filter(
            conditions__name__in=['used', 'demo']
        ).values_list('brand', flat=True).distinct())
        self.assertEqual(set(response.context['unique_makes']), expected_used_makes)

        self.assertEqual(response.context['current_condition_slug'], 'used')
        self.assertEqual(response.context['page_title'], 'Used Motorcycles')
        self.assertContains(response, 'No motorcycles match the current criteria.')


    def test_no_motorcycles_found_display_initial_load(self):
        
        response = self.client.get(reverse('inventory:all'))                                        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No motorcycles match the current criteria.')
        self.assertEqual(len(response.context['motorcycles']), 0)
        self.assertFalse(response.context['page_obj'].object_list)