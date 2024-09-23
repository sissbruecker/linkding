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
from django.urls import path, include

from bookmarks.admin import linkding_admin_site


class LinkdingLoginView(auth_views.LoginView):
    """
    Custom login view to lazily add additional context data
    Allows to override settings in tests
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["allow_registration"] = settings.ALLOW_REGISTRATION
        context["enable_oidc"] = settings.LD_ENABLE_OIDC
        return context

    def form_invalid(self, form):
        response = super().form_invalid(form)
        response.status_code = 401
        return response


class LinkdingPasswordChangeView(auth_views.PasswordChangeView):
    def form_invalid(self, form):
        response = super().form_invalid(form)
        response.status_code = 422
        return response


urlpatterns = [
    path("admin/", linkding_admin_site.urls),
    path(
        "login/",
        LinkdingLoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "change-password/",
        LinkdingPasswordChangeView.as_view(),
        name="change_password",
    ),
    path(
        "password-change-done/",
        auth_views.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path("", include("bookmarks.urls")),
]

if settings.LD_ENABLE_OIDC:
    urlpatterns.append(path("oidc/", include("mozilla_django_oidc.urls")))

if settings.LD_CONTEXT_PATH:
    urlpatterns = [path(settings.LD_CONTEXT_PATH, include(urlpatterns))]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))

if settings.ALLOW_REGISTRATION:
    urlpatterns.append(path("", include("django_registration.backends.one_step.urls")))
