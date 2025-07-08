from django.test import TestCase
from inventory.templatetags.youtube import get_youtube_id

class GetYoutubeIdFilterTest(TestCase):

    def test_standard_watch_url(self):
        url = "http://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(get_youtube_id(url), "dQw4w9WgXcQ")

    def test_short_url(self):
        url = "http://youtu.be/dQw4w9WgXcQ"
        self.assertEqual(get_youtube_id(url), "dQw4w9WgXcQ")

    def test_embed_url(self):
        url = "http://www.youtube.com/embed/dQw4w9WgXcQ"
        self.assertEqual(get_youtube_id(url), "dQw4w9WgXcQ")

    def test_v_url(self):
        url = "http://www.youtube.com/v/dQw4w9WgXcQ"
        self.assertEqual(get_youtube_id(url), "dQw4w9WgXcQ")

    def test_url_with_extra_params(self):
        url = "http://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=youtu.be"
        self.assertEqual(get_youtube_id(url), "dQw4w9WgXcQ")

    def test_invalid_youtube_url(self):
        url = "http://www.google.com"
        self.assertIsNone(get_youtube_id(url))

    def test_none_url(self):
        self.assertIsNone(get_youtube_id(None))

    def test_empty_string_url(self):
        self.assertIsNone(get_youtube_id(""))