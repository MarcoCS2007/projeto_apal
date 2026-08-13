import datetime

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.usuarios.models import Administrador, Ambulante, Fiscal, Gestor, Perfil


class UsuariosAuthFixtures:
    senha = "senha-segura-123"

    def setUp(self):
        self.ambulante = Ambulante.objects.create_user(
            cpf="33333333333",
            email="ambulante@apal.com",
            password=self.senha,
            nome="João",
            sobrenome="Ambulante",
            telefone_whatsapp="77999999999",
            tipo_atuacao="Carrinho",
            codigo_qr_code="QR-TEST-001",
            data_nasc=datetime.date(1990, 1, 1),
            escolaridade="Ensino Médio",
        )
        self.fiscal = Fiscal.objects.create_user(
            cpf="22222222222",
            email="fiscal@apal.com",
            password=self.senha,
            nome="Maria",
            sobrenome="Fiscal",
            telefone_whatsapp="77988888888",
            matricula_funcional="FIS-TEST-001",
            zona_atuacao_primaria="Centro",
        )
        self.gestor = Gestor.objects.create_user(
            cpf="11111111111",
            email="gestor@apal.com",
            password=self.senha,
            nome="Carlos",
            sobrenome="Gestor",
            telefone_whatsapp="77977777777",
            matricula_funcional="GES-TEST-001",
            cargo="Gestor de Posturas",
            departamento="Posturas",
            is_staff=True,
        )
        self.administrador = Administrador.objects.create_superuser(
            cpf="00000000000",
            email="admin@apal.com",
            password=self.senha,
            nome="Ana",
            sobrenome="Admin",
            telefone_whatsapp="77966666666",
            acesso_master=True,
        )


class LoginAPITests(UsuariosAuthFixtures, APITestCase):
    def setUp(self):
        super().setUp()
        self.url_login = "/api/login/"
        self.url_me = "/api/me/"

    def _login(self, cpf, password=None):
        return self.client.post(
            self.url_login,
            {"cpf": cpf, "password": password or self.senha},
            format="json",
        )

    def _claim_role(self, access_token):
        return AccessToken(access_token)["role"]

    def test_login_ambulante_gera_token_com_role(self):
        response = self._login(self.ambulante.cpf)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["role"], Perfil.AMBULANTE)
        self.assertEqual(self._claim_role(response.data["access"]), Perfil.AMBULANTE)
        self.assertNotIn("sessionid", response.cookies)

    def test_login_fiscal_gera_token_com_role(self):
        response = self._login(self.fiscal.cpf)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role"], Perfil.FISCAL)
        self.assertEqual(self._claim_role(response.data["access"]), Perfil.FISCAL)

    def test_login_gestor_gera_token_com_role(self):
        response = self._login(self.gestor.cpf)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._claim_role(response.data["access"]), Perfil.GESTOR)

    def test_login_administrador_gera_token_com_role(self):
        response = self._login(self.administrador.cpf)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self._claim_role(response.data["access"]), Perfil.ADMINISTRADOR
        )

    def test_login_credenciais_invalidas(self):
        response = self._login(self.ambulante.cpf, password="senha-errada")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)

    def test_login_usuario_inativo_pelo_campo_ativo(self):
        self.ambulante.ativo = False
        self.ambulante.save(update_fields=["ativo"])

        response = self._login(self.ambulante.cpf)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_com_token_jwt_retorna_perfil(self):
        login = self._login(self.fiscal.cpf)
        access = login.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.client.get(self.url_me)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["cpf"], self.fiscal.cpf)
        self.assertEqual(response.data["role"], Perfil.FISCAL)

    def test_me_sem_token_e_rejeitado(self):
        response = self.client.get(self.url_me)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LoginBackofficeTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.url_login = reverse("login")
        self.url_backoffice = reverse("backoffice_inicio")
        self.url_logout = reverse("logout")

    def _login_web(self, identificador, password=None):
        return self.client.post(
            self.url_login,
            {
                "username": identificador,
                "password": password or self.senha,
            },
        )

    def test_get_login_renderiza_template(self):
        response = self.client.get(self.url_login)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "login.html")
        self.assertContains(response, "Acesso ao Backoffice")

    def test_login_gestor_cria_cookie_de_sessao(self):
        response = self._login_web(self.gestor.cpf)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url_backoffice)
        self.assertIn("sessionid", response.cookies)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.gestor.pk)

    def test_login_administrador_com_email(self):
        response = self._login_web(self.administrador.email)

        self.assertEqual(response.status_code, 302)
        self.assertIn("sessionid", response.cookies)
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), self.administrador.pk
        )

    def test_login_ambulante_e_bloqueado(self):
        response = self._login_web(self.ambulante.cpf)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "não possui acesso ao backoffice")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_fiscal_e_bloqueado(self):
        response = self._login_web(self.fiscal.cpf)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_senha_invalida(self):
        response = self._login_web(self.gestor.cpf, password="senha-errada")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CPF/e-mail ou senha inválidos")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_backoffice_exige_autenticacao(self):
        response = self.client.get(self.url_backoffice)

        self.assertEqual(response.status_code, 302)
        self.assertIn(self.url_login, response.url)

    def test_sessao_acessa_backoffice_apos_login(self):
        self._login_web(self.gestor.cpf)
        response = self.client.get(self.url_backoffice)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.gestor.nome)
        self.assertContains(response, Perfil.GESTOR)

    def test_logout_encerra_sessao(self):
        self._login_web(self.gestor.cpf)
        response = self.client.post(self.url_logout)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
