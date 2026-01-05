from django.conf import settings
from django.contrib.auth import views as auth_views

from bookmarks.widgets import FormErrorList


class LinkdingLoginView(auth_views.LoginView):
    """
    Custom login view to lazily add additional context data
    Allows to override settings in tests
    """

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.error_class = FormErrorList
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["enable_oidc"] = settings.LD_ENABLE_OIDC
        context["disable_login"] = settings.LD_DISABLE_LOGIN_FORM
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
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.error_class = FormErrorList
        return form

    def form_invalid(self, form):
        """
        Hotwired Turbo requires a non 2xx status code to handle failed form
        submissions.
        """
        response = super().form_invalid(form)
        response.status_code = 422
        return response
