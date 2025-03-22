from django.conf import settings
from django.contrib.auth import views as auth_views


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
        """
        Return 401 status code on failed login. Should allow integrating with
        tools like Fail2Ban. Also, Hotwired Turbo requires a non 2xx status
        code to handle failed form submissions.
        """
        response = super().form_invalid(form)
        response.status_code = 401
        return response


class LinkdingPasswordChangeView(auth_views.PasswordChangeView):
    def form_invalid(self, form):
        """
        Hotwired Turbo requires a non 2xx status code to handle failed form
        submissions.
        """
        response = super().form_invalid(form)
        response.status_code = 422
        return response
