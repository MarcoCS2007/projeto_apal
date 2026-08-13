from django.views.generic import TemplateView

from apps.usuarios.lgpd import BASE_LEGAL_LGPD_ROTULO
from apps.usuarios.models import ConfiguracaoSeguranca


class HomeView(TemplateView):
    template_name = "home.html"


class SobreView(TemplateView):
    template_name = "publico/sobre.html"


class FaqView(TemplateView):
    template_name = "publico/faq.html"


class PrivacidadeView(TemplateView):
    template_name = "publico/privacidade.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_legal"] = BASE_LEGAL_LGPD_ROTULO
        context["retencao_meses"] = ConfiguracaoSeguranca.carregar().retencao_logs_meses
        return context
