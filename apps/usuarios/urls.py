from django.urls import path
from .views.viewAmbulante import RegisterAmbulanteView


urlpatterns = [
    path("", RegisterAmbulanteView.as_view(), name='register-ambulante')
]
