from django.urls import path

from .api import AssistenteAmbulanteAPIView

urlpatterns = [
    path(
        "ambulante/assistente/",
        AssistenteAmbulanteAPIView.as_view(),
        name="api_ambulante_assistente",
    ),
]
