from django.urls import path

from .views import BackofficeInicioView, LoginBackofficeView, LogoutBackofficeView

urlpatterns = [
    path("login/", LoginBackofficeView.as_view(), name="login"),
    path("logout/", LogoutBackofficeView.as_view(), name="logout"),
    path("backoffice/", BackofficeInicioView.as_view(), name="backoffice_inicio"),
]
