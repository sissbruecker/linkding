from django.http import HttpResponse

custom_css_cache_max_age = 2592000  # 30 days


def custom_css(request):
    css = request.user_profile.custom_css
    response = HttpResponse(css, content_type="text/css")
    response["Cache-Control"] = f"public, max-age={custom_css_cache_max_age}"
    return response
