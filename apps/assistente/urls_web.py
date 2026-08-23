from django.urls import path

from .views import AssistenteAmbulanteView, AssistenteGestorView

urlpatterns = [
    path(
        "ambulante/assistente/",
        AssistenteAmbulanteView.as_view(),
        name="ambulante_assistente",
    ),
    path(
        "gestor/assistente/",
        AssistenteGestorView.as_view(),
        name="gestor_assistente",
    ),
]
