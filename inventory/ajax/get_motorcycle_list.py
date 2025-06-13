# inventory/ajax/get_motorcycle_list.py

from django.http import JsonResponse, HttpRequest
from inventory.utils.get_motorcycles_by_criteria import get_motorcycles_by_criteria
from inventory.utils.get_unique_makes_for_filter import get_unique_makes_for_filter
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def get_motorcycle_list(request: HttpRequest):
    """
    AJAX endpoint to retrieve a filtered and paginated list of motorcycles and associated filter data.
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
        makes_json = request.GET.get('brand') # Changed from 'makes' to 'brand' to match HTML form name
        page_number = request.GET.get('page', 1) # Get page number, default to 1
        order_by = request.GET.get('order') # Get sort order

        # Convert numerical parameters to integers/floats if they exist
        try:
            year_min = int(year_min) if year_min else None
            year_max = int(year_max) if year_max else None
            engine_min_cc = int(engine_min_cc) if engine_min_cc else None
            engine_max_cc = int(engine_max_cc) if engine_max_cc else None
            price_min = float(price_min) if price_min else None
            price_max = float(price_max) if price_max else None
        except ValueError:
            return JsonResponse({'error': 'Invalid number format for filters'}, status=400)

        # Parse makes from JSON string (if it were a multi-select) or just use the string
        # Given the HTML select is single-select for 'brand', makes_json will be a single string.
        makes = [makes_json] if makes_json else None


        # Use the utility to get the filtered queryset
        motorcycles_queryset = get_motorcycles_by_criteria(
            condition_slug=condition_slug,
            year_min=year_min,
            year_max=year_max,
            engine_min_cc=engine_min_cc,
            engine_max_cc=engine_max_cc,
            price_min=price_min,
            price_max=price_max,
            makes=makes
        )

        # Apply sorting based on the 'order' parameter
        if order_by == 'price_low_to_high':
            motorcycles_queryset = motorcycles_queryset.order_by('price')
        elif order_by == 'price_high_to_low':
            motorcycles_queryset = motorcycles_queryset.order_by('-price')
        elif order_by == 'age_new_to_old':
            motorcycles_queryset = motorcycles_queryset.order_by('-year')
        elif order_by == 'age_old_to_new':
            motorcycles_queryset = motorcycles_queryset.order_by('year')
        # Default sorting is already applied in get_motorcycles_by_criteria if no order_by

        # Paginate the results
        paginator = Paginator(motorcycles_queryset, 10) # 10 motorcycles per page, matching ListView
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        # Serialize the motorcycles data for the current page
        motorcycles_data = []
        for bike in page_obj:
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
                'is_for_hire': bike.is_for_hire(), # Add this to determine price display
                'daily_hire_rate': float(bike.daily_hire_rate) if bike.daily_hire_rate else None, # Add hire rate
            })

        # Get unique makes relevant to the *initially filtered* set,
        # which means re-calling the utility with only the `condition_slug`.
        # This provides the full list of brands for the dropdown based on the category (new/used/all).
        unique_makes_for_filter = get_unique_makes_for_filter(condition_slug=condition_slug)


        return JsonResponse({
            'motorcycles': motorcycles_data,
            'unique_makes_for_filter': sorted(list(unique_makes_for_filter)),
            'page_obj': { # Pass pagination details to frontend
                'number': page_obj.number,
                'num_pages': page_obj.paginator.num_pages,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
                'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            }
        })
    return JsonResponse({'error': 'Invalid request method'}, status=405)

