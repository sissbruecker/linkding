"""siteroot URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path, include, re_path

from bookmarks.admin import linkding_admin_site
from .settings import ALLOW_REGISTRATION, DEBUG

urlpatterns = [
    path('admin/', linkding_admin_site.urls),
    path('login/', auth_views.LoginView.as_view(redirect_authenticated_user=True,
                                                extra_context=dict(allow_registration=ALLOW_REGISTRATION)),
         name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('change-password/', auth_views.PasswordChangeView.as_view(), name='change_password'),
    path('password-change-done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('', include('bookmarks.urls')),
    re_path(r"^opensearch/", include("opensearch.urls")),
]

if settings.LD_CONTEXT_PATH:
    urlpatterns = [path(settings.LD_CONTEXT_PATH, include(urlpatterns))]

if DEBUG:
    import debug_toolbar

    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))

if ALLOW_REGISTRATION:
    urlpatterns.append(path('', include('django_registration.backends.one_step.urls')))
