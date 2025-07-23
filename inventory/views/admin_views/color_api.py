from django.http import JsonResponse
from inventory.models import Color

def color_list_api(request):
    query = request.GET.get('q', '')
    colors = Color.objects.filter(name__icontains=query).values('id', 'name')
    return JsonResponse(list(colors), safe=False)
