from django.urls import path

from .api import CadastroAmbulanteAPIView, ScoreAmbulanteAPIView
from .views import LoginAPIView, MeView, TokenRefreshAPIView

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="api_login"),
    path("token/refresh/", TokenRefreshAPIView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path(
        "ambulante/cadastro/",
        CadastroAmbulanteAPIView.as_view(),
        name="api_ambulante_cadastro",
    ),
    path(
        "ambulante/score/", ScoreAmbulanteAPIView.as_view(), name="api_ambulante_score"
    ),
]
