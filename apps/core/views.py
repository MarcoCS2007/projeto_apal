from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "home.html"


class SobreView(TemplateView):
    template_name = "publico/sobre.html"


class FaqView(TemplateView):
    template_name = "publico/faq.html"
