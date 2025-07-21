from dashboard.models import Review

def get_reviews():
    return Review.objects.filter(is_active=True)

