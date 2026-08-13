import datetime

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from apps.assistente.models import LogAssistente
from apps.usuarios.models import (
    Administrador,
    Ambulante,
    Fiscal,
    Gestor,
    Perfil,
    UsuarioBase,
)


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

    def test_login_administrador_redireciona_ao_painel_master(self):
        response = self._login_web(self.administrador.cpf)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("master_admin"))

    def test_createsuperuser_pelo_usuario_base_cria_administrador(self):
        user = UsuarioBase.objects.create_superuser(
            cpf="99999999999",
            email="master.novo@apal.com",
            password=self.senha,
            nome="Novo",
            sobrenome="Master",
            telefone_whatsapp="77900000000",
        )

        self.assertIsInstance(user, Administrador)
        self.assertEqual(user.role, Perfil.ADMINISTRADOR)
        self.assertTrue(user.acesso_master)

        response = self._login_web(user.cpf)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("master_admin"))

    def test_superusuario_legado_sem_perfil_filho_acessa_master(self):
        legado = UsuarioBase.objects.create_user(
            cpf="12345678",
            email="a@gmail.com",
            password=self.senha,
            nome="Luan",
            sobrenome="Santos",
            telefone_whatsapp="",
            is_staff=True,
            is_superuser=True,
        )

        self.assertEqual(legado.role, Perfil.ADMINISTRADOR)
        response = self._login_web(legado.cpf)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("master_admin"))


MASTER_TELAS = (
    ("master_admin", "master/admin.html"),
    ("master_gestores", "master/controlar-gestores.html"),
    ("master_cadastrar_gestor", "master/cadastrar-gestor.html"),
    ("master_fiscais", "master/gerenciar-fiscais.html"),
    ("master_cadastrar_fiscal", "master/cadastrar-fiscal.html"),
    ("master_permissoes", "master/gerenciar-permissoes.html"),
    ("master_logs_ia", "master/logs-ia.html"),
)


class MasterViewsTests(UsuariosAuthFixtures, TestCase):
    def test_anonimo_e_redirecionado_ao_login(self):
        for name, _template in MASTER_TELAS:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response.url)

    def test_gestor_nao_acessa_painel_master(self):
        self.client.force_login(self.gestor)
        for name, _template in MASTER_TELAS:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("backoffice_inicio"))
                self.assertEqual(
                    int(self.client.session["_auth_user_id"]), self.gestor.pk
                )

    def test_administrador_abre_as_telas(self):
        self.client.force_login(self.administrador)
        for name, template in MASTER_TELAS:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)

    def test_painel_usa_contagens_reais(self):
        self.client.force_login(self.administrador)
        response = self.client.get(reverse("master_admin"))

        self.assertEqual(response.context["total_gestores_ativos"], 1)
        self.assertEqual(response.context["total_fiscais"], 1)
        self.assertEqual(response.context["total_ambulantes"], 1)
        self.assertNotContains(response, "Dra. Mariana Almeida")

    def test_painel_ignora_gestor_inativo_na_contagem(self):
        self.gestor.ativo = False
        self.gestor.save(update_fields=["ativo"])
        self.client.force_login(self.administrador)

        response = self.client.get(reverse("master_admin"))
        self.assertEqual(response.context["total_gestores_ativos"], 0)

    def test_lista_gestores_vem_do_banco(self):
        self.client.force_login(self.administrador)
        response = self.client.get(reverse("master_gestores"))

        self.assertContains(response, self.gestor.nome)
        self.assertContains(response, self.gestor.email)
        self.assertContains(response, self.gestor.departamento)
        self.assertContains(response, self.gestor.cargo)
        self.assertNotContains(response, "Dra. Mariana Almeida")

    def test_busca_gestores_filtra_por_nome(self):
        self.client.force_login(self.administrador)
        encontrados = self.client.get(reverse("master_gestores"), {"q": "Carlos"})
        vazios = self.client.get(reverse("master_gestores"), {"q": "inexistente"})

        self.assertContains(encontrados, self.gestor.nome)
        self.assertContains(vazios, "Nenhum gestor cadastrado")
        self.assertNotContains(vazios, self.gestor.email)

    def test_lista_fiscais_vem_do_banco(self):
        self.client.force_login(self.administrador)
        response = self.client.get(reverse("master_fiscais"))

        self.assertContains(response, self.fiscal.nome)
        self.assertContains(response, self.fiscal.matricula_funcional)
        self.assertContains(response, self.fiscal.zona_atuacao_primaria)
        self.assertNotContains(response, "Carlos Eduardo Moreira")

    def test_logs_ia_vem_do_banco(self):
        LogAssistente.objects.create(
            ambulante=self.ambulante,
            pergunta="O que é alvará digital?",
        )
        self.client.force_login(self.administrador)
        response = self.client.get(reverse("master_logs_ia"))

        self.assertEqual(response.context["total_logs"], 1)
        self.assertContains(response, "O que é alvará digital?")
        self.assertContains(response, self.ambulante.nome)
        self.assertNotContains(response, "Alvará Precário")

    def _payload_gestor(self, **overrides):
        dados = {
            "nome_completo": "Mariana Almeida",
            "cpf": "44455566677",
            "email": "mariana.almeida@pmvc.ba.gov.br",
            "telefone_whatsapp": "77911111111",
            "departamento": "SESEP - Serviços Públicos (Posturas)",
            "cargo": "Coordenadora de Licenciamento",
            "password": self.senha,
        }
        dados.update(overrides)
        return dados

    def _payload_fiscal(self, **overrides):
        dados = {
            "nome_completo": "Carlos Eduardo Moreira",
            "matricula_funcional": "FIS-4599",
            "cpf": "55566677788",
            "email": "carlos.moreira@pmvc.ba.gov.br",
            "zona_atuacao_primaria": "Centro Comercial / Praça 9 de Novembro",
            "password": self.senha,
        }
        dados.update(overrides)
        return dados

    def test_cadastrar_gestor_salva_no_banco(self):
        self.client.force_login(self.administrador)
        response = self.client.post(
            reverse("master_cadastrar_gestor"),
            self._payload_gestor(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("master_gestores"))
        gestor = Gestor.objects.get(cpf="44455566677")
        self.assertEqual(gestor.nome, "Mariana")
        self.assertEqual(gestor.sobrenome, "Almeida")
        self.assertEqual(gestor.departamento, "SESEP - Serviços Públicos (Posturas)")
        self.assertEqual(gestor.matricula_funcional, "GES-44455566677")
        self.assertTrue(gestor.is_staff)
        self.assertTrue(gestor.check_password(self.senha))

    def test_cadastrar_gestor_cpf_duplicado(self):
        self.client.force_login(self.administrador)
        response = self.client.post(
            reverse("master_cadastrar_gestor"),
            self._payload_gestor(cpf=self.gestor.cpf),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Já existe um usuário com este CPF")
        self.assertEqual(Gestor.objects.filter(email="mariana.almeida@pmvc.ba.gov.br").count(), 0)

    def test_cadastrar_fiscal_salva_no_banco(self):
        self.client.force_login(self.administrador)
        response = self.client.post(
            reverse("master_cadastrar_fiscal"),
            self._payload_fiscal(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("master_fiscais"))
        fiscal = Fiscal.objects.get(matricula_funcional="FIS-4599")
        self.assertEqual(fiscal.nome, "Carlos")
        self.assertEqual(fiscal.cpf, "55566677788")
        self.assertEqual(
            fiscal.zona_atuacao_primaria,
            "Centro Comercial / Praça 9 de Novembro",
        )
        self.assertTrue(fiscal.check_password(self.senha))

    def test_gestor_nao_pode_cadastrar_fiscal(self):
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse("master_cadastrar_fiscal"),
            self._payload_fiscal(),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backoffice_inicio"))
        self.assertFalse(Fiscal.objects.filter(cpf="55566677788").exists())
