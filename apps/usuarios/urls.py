from django.urls import path

from .views import LoginAPIView, MeView, TokenRefreshAPIView

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="api_login"),
    path("token/refresh/", TokenRefreshAPIView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
]
