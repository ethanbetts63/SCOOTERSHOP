from django.http import JsonResponse
from django.db.models import Q
from inventory.models import Motorcycle
from django.core.paginator import Paginator

def get_motorcycle_list(request):
    # Base queryset
    motorcycles = Motorcycle.objects.filter(is_available=True)

    # Condition filtering
    condition_slug = request.GET.get('condition_slug', 'all')
    if condition_slug in ['new', 'used', 'demo']:
        condition_filter = Q(condition=condition_slug) | Q(conditions__name__iexact=condition_slug)
        motorcycles = motorcycles.filter(condition_filter).distinct()

    # Brand filtering
    brand = request.GET.get('brand')
    if brand:
        motorcycles = motorcycles.filter(brand__iexact=brand)

    # Year filtering
    year_min = request.GET.get('year_min')
    year_max = request.GET.get('year_max')
    if year_min:
        motorcycles = motorcycles.filter(year__gte=year_min)
    if year_max:
        motorcycles = motorcycles.filter(year__lte=year_max)

    # Price filtering
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        motorcycles = motorcycles.filter(price__gte=price_min)
    if price_max:
        motorcycles = motorcycles.filter(price__lte=price_max)

    # Engine size filtering
    engine_min_cc = request.GET.get('engine_min_cc')
    engine_max_cc = request.GET.get('engine_max_cc')
    if engine_min_cc:
        motorcycles = motorcycles.filter(engine_size__gte=engine_min_cc)
    if engine_max_cc:
        motorcycles = motorcycles.filter(engine_size__lte=engine_max_cc)

    # Sorting
    sort_order = request.GET.get('order')
    if sort_order == 'price_low_to_high':
        motorcycles = motorcycles.order_by('price')
    elif sort_order == 'price_high_to_low':
        motorcycles = motorcycles.order_by('-price')
    elif sort_order == 'age_new_to_old':
        motorcycles = motorcycles.order_by('-year')
    elif sort_order == 'age_old_to_new':
        motorcycles = motorcycles.order_by('year')
    else:
        motorcycles = motorcycles.order_by('-date_posted')

    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(motorcycles, 9)  # 9 motorcycles per page
    page_obj = paginator.get_page(page_number)

    motorcycle_data = []
    for bike in page_obj:
        motorcycle_data.append({
            'id': bike.pk,
            'title': bike.title,
            'brand': bike.brand,
            'model': bike.model,
            'year': bike.year,
            'price': bike.price,
            'image_url': bike.image.url if bike.image else None,
            'condition_display': bike.get_conditions_display(),
            'engine_size': bike.engine_size,
            'odometer': bike.odometer,
            'detail_url': bike.get_absolute_url(),
            'transmission': bike.transmission,
            'status': bike.status,
            'quantity': bike.quantity,
            'condition_name': bike.condition
        })

    return JsonResponse({
        'motorcycles': motorcycle_data,
        'page_obj': {
            'number': page_obj.number,
            'num_pages': page_obj.paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'has_next': page_obj.has_next(),
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
        }
    })
