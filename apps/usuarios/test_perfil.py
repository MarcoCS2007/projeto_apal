import pytest
import io
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.espacos.models import Endereco, EstruturaTrabalho
from apps.usuarios.models import Ambulante
from apps.usuarios.tests import UsuariosAuthFixtures


class PerfilAmbulanteTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("ambulante_perfil")
        self.ambulante.dados_complementares = {
            "rg": "1234567",
            "razao_social": "João Lanches ME",
        }
        self.ambulante.apelido_nome_fantasia = "João Lanches"
        self.ambulante.cnpj = "12345678000199"
        self.ambulante.save()
        Endereco.objects.create(
            ambulante=self.ambulante,
            cep="45000-000",
            logradouro="Rua das Flores",
            numero="100",
            complemento="Casa",
            bairro="Centro",
            cidade="Vitória da Conquista",
            estado_uf="BA",
        )
        EstruturaTrabalho.objects.create(
            ambulante=self.ambulante,
            tipo_estrutura="carrinho",
            dimensoes_metragem="2.50",
            descricao="Lanches e sucos",
        )

    def _payload(self, **extra):
        dados = {
            "email": self.ambulante.email,
            "renda_mensal_estimada": self.ambulante.renda_mensal_estimada or "1800.00",
            "telefone_whatsapp": self.ambulante.telefone_whatsapp,
            "telefone_2": self.ambulante.telefone_2 or "",
            "cep": "45000-000",
            "logradouro": "Rua das Flores",
            "numero": "100",
            "complemento": "Casa",
            "bairro": "Centro",
            "estado_uf": "BA",
            "cidade": "Vitória da Conquista",
        }
        dados.update(extra)
        return dados

    def _foto(self, nome="foto3x4.png"):
        buffer = io.BytesIO()
        Image.new("RGB", (96, 128), color="blue").save(buffer, format="PNG")
        return SimpleUploadedFile(nome, buffer.getvalue(), content_type="image/png")

    def test_anonimo_e_redirecionado_ao_entrar(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("entrar"), response.url)

    def test_gestor_nao_acessa_perfil_do_ambulante(self):
        self.client.force_login(self.gestor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backoffice_inicio"))

    def test_exibe_dados_pessoais_e_endereco(self):
        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ambulante/perfil.html")
        self.assertContains(response, "Dados pessoais")
        self.assertContains(response, "Foto 3x4")
        self.assertContains(response, "Endereço residencial")
        self.assertContains(response, self.ambulante.nome_completo)
        self.assertContains(response, self.ambulante.email)
        self.assertContains(response, "Rua das Flores")
        self.assertContains(response, "Editar perfil")
        self.assertNotContains(response, "Atividade e ponto")
        self.assertContains(
            response,
            "Visualize seus dados cadastrais e gerencie suas informações de acesso.",
        )
        self.assertNotContains(response, 'id="perfil-foto"')
        self.assertNotContains(response, "Inserir ou atualizar foto")
        self.assertNotContains(response, "alert(")

        edicao = self.client.get(f"{self.url}?editar=1")
        self.assertContains(edicao, 'id="perfil-foto"')
        self.assertContains(edicao, "Inserir ou atualizar foto")
        self.assertContains(edicao, "Salvar perfil")
        self.assertContains(edicao, "Cancelar")
        self.assertContains(edicao, 'id="perfil-renda"')
        self.assertContains(edicao, 'id="perfil-telefone"')
        self.assertContains(edicao, 'id="cpf-cadastro"')
        self.assertContains(edicao, "Trocar senha")
        self.assertContains(edicao, 'id="perfil-senha-atual"')
        self.assertNotContains(edicao, 'name="cpf"')
        self.assertNotContains(response, "Trocar senha")

    def test_atualiza_email_renda_telefone_e_endereco_sem_alterar_cpf(self):
        cpf_original = self.ambulante.cpf
        self.client.force_login(self.ambulante)
        response = self.client.post(
            self.url,
            self._payload(
                email="novo.ambulante@apal.com",
                renda_mensal_estimada="2500.50",
                telefone_whatsapp="77988887777",
                telefone_2="7732211000",
                logradouro="Avenida Brasil",
                numero="200",
                bairro="Recreio",
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Perfil atualizado")
        self.assertContains(response, "form-success")
        self.assertContains(response, "toast-container")
        self.assertNotContains(response, "alert(")
        self.ambulante.refresh_from_db()
        self.assertEqual(self.ambulante.email, "novo.ambulante@apal.com")
        self.assertEqual(self.ambulante.cpf, cpf_original)
        self.assertEqual(str(self.ambulante.renda_mensal_estimada), "2500.50")
        self.assertEqual(self.ambulante.telefone_whatsapp, "77988887777")
        self.assertEqual(self.ambulante.telefone_2, "7732211000")
        endereco = self.ambulante.enderecos.order_by("id").first()
        self.assertEqual(endereco.logradouro, "Avenida Brasil")
        self.assertEqual(endereco.numero, "200")
        self.assertEqual(endereco.bairro, "Recreio")

    def test_atualiza_foto_no_perfil(self):
        self.client.force_login(self.ambulante)
        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            response = self.client.post(
                self.url,
                self._payload(foto=self._foto()),
                follow=True,
            )

            self.assertEqual(response.status_code, 200)
            self.ambulante.refresh_from_db()
            self.assertTrue(self.ambulante.foto)
            self.assertIn("usuarios/fotos/", self.ambulante.foto.name)

    def test_rejeita_email_duplicado_com_notificacao(self):
        Ambulante.objects.create_user(
            cpf="55555555555",
            email="ocupado@apal.com",
            password=self.senha,
            nome="Outro",
            sobrenome="Ambulante",
            telefone_whatsapp="77911111111",
        )
        self.client.force_login(self.ambulante)
        response = self.client.post(
            self.url,
            self._payload(email="ocupado@apal.com"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Já existe um usuário com este e-mail.")
        self.assertContains(response, "Não foi possível salvar o perfil")
        self.assertContains(response, "mostrarToast")
        self.assertNotContains(response, "alert(")
        self.ambulante.refresh_from_db()
        self.assertEqual(self.ambulante.email, "ambulante@apal.com")

    def test_troca_senha_com_senha_atual(self):
        self.client.force_login(self.ambulante)
        nova = "nova-senha-segura-456"
        response = self.client.post(
            self.url,
            self._payload(
                senha_atual=self.senha,
                senha_nova=nova,
                senha_nova_confirmacao=nova,
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A senha foi alterada com sucesso")
        self.ambulante.refresh_from_db()
        self.assertTrue(self.ambulante.check_password(nova))
        self.assertFalse(self.ambulante.check_password(self.senha))

    def test_rejeita_troca_senha_sem_senha_atual_correta(self):
        self.client.force_login(self.ambulante)
        response = self.client.post(
            self.url,
            self._payload(
                senha_atual="senha-errada",
                senha_nova="nova-senha-segura-456",
                senha_nova_confirmacao="nova-senha-segura-456",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senha atual incorreta")
        self.ambulante.refresh_from_db()
        self.assertTrue(self.ambulante.check_password(self.senha))

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_cadastro_nao_tem_upload_de_foto_e_aponta_para_o_perfil(self):
        self.client.force_login(self.ambulante)
        response = self.client.get(reverse("ambulante_cadastro"))

        self.assertNotContains(response, 'id="req-foto"')
        self.assertNotContains(response, 'id="perfil-foto"')
        self.assertContains(response, reverse("ambulante_perfil"))
        self.assertContains(response, "Dados Pessoais do Requerente")
