# inventory/ajax/get_motorcycle_list.py

from django.http import JsonResponse, HttpRequest
from inventory.utils.get_motorcycles_by_criteria import get_motorcycles_by_criteria
import json

def get_motorcycle_list(request: HttpRequest):
    """
    AJAX endpoint to retrieve a filtered list of motorcycles and associated filter data.
    Filters are applied based on query parameters received in the GET request.
    """
    if request.method == 'GET':
        condition_slug = request.GET.get('condition_slug')
        year_min = request.GET.get('year_min')
        year_max = request.GET.get('year_max')
        engine_min_cc = request.GET.get('engine_min_cc')
        engine_max_cc = request.GET.get('engine_max_cc')
        price_min = request.GET.get('price_min')
        price_max = request.GET.get('price_max')
        makes_json = request.GET.get('makes') # This will be a JSON string from the frontend

        # Convert year, engine_size, and price parameters to integers/floats if they exist
        try:
            year_min = int(year_min) if year_min else None
            year_max = int(year_max) if year_max else None
            engine_min_cc = int(engine_min_cc) if engine_min_cc else None
            engine_max_cc = int(engine_max_cc) if engine_max_cc else None
            price_min = float(price_min) if price_min else None
            price_max = float(price_max) if price_max else None
        except ValueError:
            return JsonResponse({'error': 'Invalid number format for filters'}, status=400)

        # Parse makes from JSON string to a Python list
        makes = []
        if makes_json:
            try:
                makes = json.loads(makes_json)
                if not isinstance(makes, list):
                    raise ValueError("Makes parameter must be a JSON array.")
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON format for makes filter'}, status=400)
            except ValueError as e:
                return JsonResponse({'error': str(e)}, status=400)


        # Handle 'used' condition to include 'demo'
        if condition_slug == 'used':
            # Get motorcycles for 'used'
            used_motorcycles = get_motorcycles_by_criteria(
                condition_slug='used',
                year_min=year_min,
                year_max=year_max,
                engine_min_cc=engine_min_cc,
                engine_max_cc=engine_max_cc,
                price_min=price_min,
                price_max=price_max,
                makes=makes
            )
            # Get motorcycles for 'demo'
            demo_motorcycles = get_motorcycles_by_criteria(
                condition_slug='demo',
                year_min=year_min,
                year_max=year_max,
                engine_min_cc=engine_min_cc,
                engine_max_cc=engine_max_cc,
                price_min=price_min,
                price_max=price_max,
                makes=makes
            )
            # Combine the querysets and remove duplicates
            motorcycles = (used_motorcycles | demo_motorcycles).distinct()
        elif condition_slug == 'all': # Admin functionality, display all conditions
            motorcycles = get_motorcycles_by_criteria(
                condition_slug=None, # Pass None to get_motorcycles_by_criteria to fetch all
                year_min=year_min,
                year_max=year_max,
                engine_min_cc=engine_min_cc,
                engine_max_cc=engine_max_cc,
                price_min=price_min,
                price_max=price_max,
                makes=makes
            )
        else: # 'new' or any other specific condition
            motorcycles = get_motorcycles_by_criteria(
                condition_slug=condition_slug,
                year_min=year_min,
                year_max=year_max,
                engine_min_cc=engine_min_cc,
                engine_max_cc=engine_max_cc,
                price_min=price_min,
                price_max=price_max,
                makes=makes
            )

        # Prepare the condition slugs for `get_unique_makes_for_filter`
        makes_condition_slugs = []
        if condition_slug == 'used':
            makes_condition_slugs = ['used', 'demo']
        elif condition_slug == 'all':
            makes_condition_slugs = [None] # Represents all conditions
        else:
            makes_condition_slugs = [condition_slug]

        # Let's get the makes from the *resultant* `motorcycles` queryset directly for accuracy
        current_unique_makes = sorted(list(motorcycles.values_list('brand', flat=True).distinct()))


        # Serialize the motorcycles data
        motorcycles_data = []
        for bike in motorcycles:
            motorcycles_data.append({
                'id': bike.id,
                'title': bike.title,
                'brand': bike.brand,
                'model': bike.model,
                'year': bike.year,
                'price': float(bike.price) if bike.price else None, # Convert Decimal to float
                'image_url': bike.image.url if bike.image else None,
                'condition_display': bike.get_conditions_display(),
                'engine_size': bike.engine_size,
                'odometer': bike.odometer,
                'seats': bike.seats,
                'transmission': bike.transmission,
                'description': bike.description,
                'is_available': bike.is_available,
            })

        return JsonResponse({
            'motorcycles': motorcycles_data,
            'unique_makes_for_filter': current_unique_makes, # Renamed for clarity on client side
        })
    return JsonResponse({'error': 'Invalid request method'}, status=405)

