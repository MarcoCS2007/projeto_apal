from django.urls import path

from .views import FaqView, HomeView, SobreView

urlpatterns = [
    path("", HomeView.as_view(), name="index"),
    path("sobre/", SobreView.as_view(), name="sobre"),
    path("faq/", FaqView.as_view(), name="faq"),
]
