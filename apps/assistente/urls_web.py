from django.urls import path

from .views import AssistenteAmbulanteView

urlpatterns = [
    path(
        "ambulante/assistente/",
        AssistenteAmbulanteView.as_view(),
        name="ambulante_assistente",
    ),
]
