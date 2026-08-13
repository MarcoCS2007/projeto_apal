from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from apps.core.permissions import IsAdministrador, IsAmbulante, IsFiscal, IsGestor
from apps.usuarios.models import Administrador, Ambulante, Fiscal, Gestor, Perfil


class PermissoesPorPerfilTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.ambulante = Ambulante(
            cpf="33333333333",
            nome="João",
            sobrenome="Ambulante",
            email="ambulante@apal.com",
        )
        self.fiscal = Fiscal(
            cpf="22222222222",
            nome="Maria",
            sobrenome="Fiscal",
            email="fiscal@apal.com",
        )
        self.gestor = Gestor(
            cpf="11111111111",
            nome="Carlos",
            sobrenome="Gestor",
            email="gestor@apal.com",
        )
        self.administrador = Administrador(
            cpf="00000000000",
            nome="Ana",
            sobrenome="Admin",
            email="admin@apal.com",
        )

    def _request(self, user):
        request = self.factory.get("/api/me/")
        request.user = user
        return request

    def test_role_de_cada_perfil(self):
        self.assertEqual(self.ambulante.role, Perfil.AMBULANTE)
        self.assertEqual(self.fiscal.role, Perfil.FISCAL)
        self.assertEqual(self.gestor.role, Perfil.GESTOR)
        self.assertEqual(self.administrador.role, Perfil.ADMINISTRADOR)

    def test_is_ambulante_permite_somente_ambulante(self):
        permissao = IsAmbulante()
        self.assertTrue(permissao.has_permission(self._request(self.ambulante), None))
        self.assertFalse(permissao.has_permission(self._request(self.fiscal), None))

    def test_is_fiscal_permite_somente_fiscal(self):
        permissao = IsFiscal()
        self.assertTrue(permissao.has_permission(self._request(self.fiscal), None))
        self.assertFalse(permissao.has_permission(self._request(self.gestor), None))

    def test_is_gestor_e_administrador(self):
        self.assertTrue(IsGestor().has_permission(self._request(self.gestor), None))
        self.assertTrue(
            IsAdministrador().has_permission(self._request(self.administrador), None)
        )
        self.assertFalse(
            IsAdministrador().has_permission(self._request(self.gestor), None)
        )


class HomeViewTests(TestCase):
    def test_index_renderiza_landing(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")
        self.assertContains(response, "comércio ambulante organizado")
        self.assertContains(response, reverse("entrar"))
        self.assertContains(response, reverse("registro"))
        self.assertContains(response, reverse("login"))
        self.assertContains(response, reverse("fiscal_entrar"))
        self.assertContains(response, "Área institucional")
        self.assertContains(response, "Onde você faz login?")
        self.assertNotContains(response, "Acesso ao sistema")
        self.assertContains(response, reverse("sobre"))
        self.assertContains(response, reverse("faq"))


class PaginasPublicasTests(TestCase):
    def test_sobre_usa_static_e_urls_django(self):
        response = self.client.get(reverse("sobre"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "publico/sobre.html")
        self.assertContains(response, reverse("index"))
        self.assertContains(response, reverse("faq"))
        self.assertNotContains(response, "../css/style.css")
        self.assertContains(response, "static/css/style.css")

    def test_faq_usa_static_e_urls_django(self):
        response = self.client.get(reverse("faq"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "publico/faq.html")
        self.assertContains(response, reverse("registro"))
        self.assertContains(response, "static/assets/formulario.pdf")
        self.assertNotContains(response, "../css/style.css")
        self.assertNotContains(response, "../js/script.js")
