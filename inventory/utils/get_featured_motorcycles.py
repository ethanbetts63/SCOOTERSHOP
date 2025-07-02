
from inventory.models import FeaturedMotorcycle

def get_featured_motorcycles(category):
    if category not in ['new', 'used']:
        return FeaturedMotorcycle.objects.none()

    return FeaturedMotorcycle.objects.filter(
        category=category
    ).select_related('motorcycle').order_by('order')
