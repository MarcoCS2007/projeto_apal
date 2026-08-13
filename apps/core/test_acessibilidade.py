from django.test import TestCase
from django.urls import reverse

from apps.usuarios.tests import MASTER_TELAS, UsuariosAuthFixtures

WIDGET = 'id="access-widget-container"'
SKIP = "Pular para o conteúdo"


class AcessibilidadeTransversalTests(UsuariosAuthFixtures, TestCase):
    def _assert_widget_unico(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, WIDGET, count=1)
        self.assertContains(response, SKIP)
        self.assertTemplateUsed(response, "base.html")

    def test_telas_master_herdam_widget(self):
        self.client.force_login(self.administrador)
        for name, template in MASTER_TELAS:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self._assert_widget_unico(response)
                self.assertTemplateUsed(response, template)

    def test_cadastro_herda_widget_e_navega_etapas_pelo_teclado(self):
        self.client.force_login(self.ambulante)
        etapa1 = self.client.get(reverse("ambulante_cadastro"))
        self._assert_widget_unico(etapa1)
        self.assertContains(etapa1, 'aria-label="Etapas do cadastro"')
        self.assertContains(etapa1, 'aria-current="step"')
        self.assertNotContains(etapa1, "?etapa=2")

        etapa3 = self.client.get(f"{reverse('ambulante_cadastro')}?etapa=3")
        self._assert_widget_unico(etapa3)
        self.assertContains(etapa3, "?etapa=1")
        self.assertContains(etapa3, "?etapa=2")

    def test_triagem_herda_widget_e_dialogo_com_label(self):
        self.client.force_login(self.gestor)
        response = self.client.get(reverse("gestor_triagem"))
        self._assert_widget_unico(response)
        self.assertContains(response, 'role="dialog"')
        self.assertContains(response, 'for="justificativa-rejeicao"')
        self.assertContains(response, "Justificativa da recusa")
        self.assertNotContains(response, 'class="sr-only" style="display: none;"')

    def test_home_herda_widget(self):
        response = self.client.get(reverse("index"))
        self._assert_widget_unico(response)
        self.assertTemplateUsed(response, "home.html")
