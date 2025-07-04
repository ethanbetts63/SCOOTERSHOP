from django import template
from urllib.parse import urlparse, parse_qs

register = template.Library()

@register.filter(name='get_youtube_id')
def get_youtube_id(url):
    """
    A Django template filter to extract the YouTube video ID from a URL.
    
    Examples:
    - http://www.youtube.com/watch?v=dQw4w9WgXcQ -> dQw4w9WgXcQ
    - http://youtu.be/dQw4w9WgXcQ -> dQw4w9WgXcQ
    - http://www.youtube.com/embed/dQw4w9WgXcQ -> dQw4w9WgXcQ
    """
    if url is None:
        return None
    
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p.get('v', [None])[0]
        if query.path.startswith('/embed/'):
            return query.path.split('/')[2]
        if query.path.startswith('/v/'):
            return query.path.split('/')[2]
            
    return None
