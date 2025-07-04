from django.http import JsonResponse
from django.db.models import Q
from inventory.models import Motorcycle

def get_motorcycle_list(request):
    condition_slug = request.GET.get('condition_slug', 'all')
    motorcycles = Motorcycle.objects.filter(is_available=True, status='for_sale')
    if condition_slug in ['new', 'used', 'demo']:
        condition_filter = Q(condition=condition_slug) | Q(conditions__name__iexact=condition_slug)
        motorcycles = motorcycles.filter(condition_filter).distinct()

    motorcycle_data = []
    for bike in motorcycles.order_by('-date_posted'):
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

    return JsonResponse({'motorcycles': motorcycle_data})
