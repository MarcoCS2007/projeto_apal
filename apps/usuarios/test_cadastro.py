from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.espacos.models import Endereco, EstruturaTrabalho, PontoOcupacao
from apps.usuarios.models import Ambulante
from apps.usuarios.tests import UsuariosAuthFixtures


class CadastroCompletoAmbulanteTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("ambulante_cadastro")
        self.ponto = PontoOcupacao.objects.create(
            nome_identificacao="Praça Central",
            logradouro="Praça Central",
            bairro="Centro",
            metragem_maxima=Decimal("10.00"),
            status_ocupacao="Livre",
        )

    def _post_etapa(self, etapa, dados, acao="proxima"):
        payload = {"etapa": etapa, "acao": acao}
        payload.update(dados)
        return self.client.post(self.url, payload)

    def test_anonimo_e_redirecionado_ao_entrar(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("entrar"), response.url)

    def test_gestor_nao_acessa_cadastro_do_ambulante(self):
        self.client.force_login(self.gestor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backoffice_inicio"))

    def test_get_etapa_1_preenche_dados_da_conta(self):
        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ambulante/cadastro.html")
        self.assertContains(response, self.ambulante.cpf)
        self.assertContains(response, self.ambulante.nome)

    def test_salva_rascunho_da_etapa_1_e_avanca(self):
        self.client.force_login(self.ambulante)
        response = self._post_etapa(
            1,
            {
                "nome_completo": "João Ambulante Silva",
                "data_nasc": "1991-05-20",
                "telefone_whatsapp": "77999999999",
                "escolaridade": "medio_completo",
                "num_funcionarios": "1",
                "nis": "123456",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("etapa=2", response.url)
        self.ambulante.refresh_from_db()
        self.assertEqual(self.ambulante.data_nasc.isoformat(), "1991-05-20")
        self.assertEqual(self.ambulante.escolaridade, "medio_completo")
        self.assertEqual(self.ambulante.nis, "123456")
        self.assertFalse(self.ambulante.cadastro_completo)

    def test_salva_endereco_na_etapa_2(self):
        self.client.force_login(self.ambulante)
        response = self._post_etapa(
            2,
            {
                "cep": "45000-000",
                "logradouro": "Rua das Flores",
                "numero": "100",
                "bairro": "Centro",
                "estado_uf": "BA",
                "cidade": "Vitória da Conquista",
            },
        )

        self.assertEqual(response.status_code, 302)
        endereco = Endereco.objects.get(ambulante=self.ambulante)
        self.assertEqual(endereco.logradouro, "Rua das Flores")
        self.assertEqual(endereco.estado_uf, "BA")

    def test_cnpj_opcional_quando_nao_possui_mei(self):
        self.client.force_login(self.ambulante)
        response = self._post_etapa(
            3,
            {
                "sem_cnpj": "on",
                "apelido_nome_fantasia": "Carrinho do João",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.ambulante.refresh_from_db()
        self.assertIsNone(self.ambulante.cnpj)
        self.assertEqual(self.ambulante.apelido_nome_fantasia, "Carrinho do João")

    def test_metragem_nao_positiva_e_rejeitada(self):
        self.client.force_login(self.ambulante)
        response = self._post_etapa(
            4,
            {
                "tipo_atuacao": "fixo",
                "tipo_estrutura": "carrinho",
                "descricao": "Lanches",
                "dimensoes_metragem": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(EstruturaTrabalho.objects.filter(ambulante=self.ambulante).exists())

    def test_fluxo_completo_aparece_na_listagem_do_gestor(self):
        novo = Ambulante.objects.create_user(
            cpf="66677788899",
            email="joana.cadastro@email.com",
            password=self.senha,
            nome="Joana",
            sobrenome="Nova",
            telefone_whatsapp="77944444444",
        )
        self.client.force_login(novo)
        self._post_etapa(
            1,
            {
                "nome_completo": "Joana Nova",
                "data_nasc": "1990-01-01",
                "telefone_whatsapp": "77944444444",
                "escolaridade": "medio_completo",
                "num_funcionarios": "0",
            },
        )
        self._post_etapa(
            2,
            {
                "cep": "45000000",
                "logradouro": "Rua A",
                "numero": "10",
                "bairro": "Centro",
                "estado_uf": "BA",
                "cidade": "Vitória da Conquista",
            },
        )
        self._post_etapa(
            3,
            {"sem_cnpj": "on", "apelido_nome_fantasia": "Doce Joana"},
        )
        self._post_etapa(
            4,
            {
                "tipo_atuacao": "fixo",
                "tipo_estrutura": "carrinho",
                "descricao": "Doces",
                "dimensoes_metragem": "2.50",
            },
        )
        self._post_etapa(5, {"ponto_pretendido": self.ponto.pk})
        response = self._post_etapa(6, {}, acao="enviar")

        self.assertEqual(response.status_code, 302)
        self.assertIn("concluido=1", response.url)
        novo.refresh_from_db()
        self.assertTrue(novo.cadastro_completo)
        self.assertIsNone(novo.codigo_qr_code)
        self.assertEqual(novo.ponto_pretendido_id, self.ponto.pk)

        self.client.logout()
        self.client.force_login(self.gestor)
        lista = self.client.get(reverse("gestor_ambulantes"))
        self.assertEqual(lista.status_code, 200)
        self.assertContains(lista, "Joana")
        self.assertContains(lista, novo.cpf)
        self.assertContains(lista, "Cadastro completo")
        self.assertNotContains(lista, "João da Silva Santos")

    def test_concluir_sem_etapas_obrigatorias_nao_fecha_cadastro(self):
        self.client.force_login(self.ambulante)
        response = self._post_etapa(6, {}, acao="enviar")

        self.assertEqual(response.status_code, 302)
        self.ambulante.refresh_from_db()
        self.assertFalse(self.ambulante.cadastro_completo)

    def test_painel_tem_cta_para_completar_cadastro(self):
        self.client.force_login(self.ambulante)
        response = self.client.get(reverse("ambulante_painel"))
        self.assertContains(response, reverse("ambulante_cadastro"))
        self.assertContains(response, "Completar cadastro")
