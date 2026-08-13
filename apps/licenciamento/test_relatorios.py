import json
from datetime import time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.espacos.models import (
    Endereco,
    EstruturaTrabalho,
    PontoOcupacao,
    StatusOcupacao,
)
from apps.fiscalizacao.models import TipoOcorrencia
from apps.fiscalizacao.services import registrar_ocorrencia
from apps.licenciamento.models import CategoriaProduto, StatusLicenca
from apps.licenciamento.relatorios import indicadores_gerenciais
from apps.licenciamento.services import abrir_requerimento, emitir_alvara
from apps.usuarios.tests import UsuariosAuthFixtures


class DashboardIndicadoresTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.categoria = CategoriaProduto.objects.create(
            nome_categoria="Vestuário",
            descricao="Roupas e acessórios.",
        )
        self.ponto_brasil = PontoOcupacao.objects.create(
            nome_identificacao="Feira do Bairro Brasil",
            logradouro="Rua da Feira",
            bairro="Brasil",
            metragem_maxima=Decimal("12.00"),
            status_ocupacao=StatusOcupacao.LIVRE,
        )
        self.ponto_brasil_livre = PontoOcupacao.objects.create(
            nome_identificacao="Feira 2",
            logradouro="Rua B",
            bairro="Brasil",
            metragem_maxima=Decimal("8.00"),
            status_ocupacao=StatusOcupacao.LIVRE,
        )
        self.ponto_centro = PontoOcupacao.objects.create(
            nome_identificacao="Praça Central",
            logradouro="Praça Barão",
            bairro="Centro",
            metragem_maxima=Decimal("10.00"),
            status_ocupacao=StatusOcupacao.LIVRE,
        )
        self._completar(self.ambulante)
        self.licenca, _criado = abrir_requerimento(self.ambulante, self.categoria)
        self.licenca.status = StatusLicenca.APROVADO
        self.licenca.ponto_ocupacao = self.ponto_brasil
        self.licenca.categoria_produto = self.categoria
        self.licenca.save()
        self.url = reverse("gestor_dashboard")
        self.url_api = reverse("api_relatorios_ocupacao")

    def _completar(self, ambulante):
        ambulante.tipo_atuacao = "fixo"
        ambulante.ponto_pretendido = self.ponto_brasil
        ambulante.save()
        if not ambulante.enderecos.exists():
            Endereco.objects.create(
                ambulante=ambulante,
                cep="45000-000",
                logradouro="Rua A",
                numero="10",
                bairro="Brasil",
                cidade="Vitória da Conquista",
                estado_uf="BA",
            )
        if not ambulante.estruturas.exists():
            EstruturaTrabalho.objects.create(
                ambulante=ambulante,
                tipo_estrutura="barraca",
                dimensoes_metragem=Decimal("4.00"),
                descricao="Roupas",
            )

    def _emitir(self):
        hoje = timezone.localdate()
        return emitir_alvara(
            self.licenca,
            self.gestor,
            data_emissao=hoje,
            data_vencimento=hoje + timedelta(days=365),
            ponto=self.ponto_brasil,
            dias_semana=["segunda", "terca", "quarta", "quinta", "sexta"],
            horario_inicio=time(6, 0),
            horario_termino=time(18, 0),
        )

    def test_anonimo_e_fiscal_nao_acessam(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.fiscal)
        fiscal = self.client.get(self.url)
        self.assertEqual(fiscal.status_code, 302)
        self.assertEqual(fiscal.url, reverse("fiscal_painel"))

    def test_gestor_ve_numeros_do_banco_e_filtra_por_bairro(self):
        self._emitir()
        registrar_ocorrencia(
            self.fiscal,
            self.ambulante,
            TipoOcorrencia.ADVERTENCIA,
            "Uso irregular da calçada.",
            local_ocorrencia="Feira do Bairro Brasil",
        )
        self.ponto_brasil.refresh_from_db()
        self.assertEqual(self.ponto_brasil.status_ocupacao, StatusOcupacao.OCUPADO)

        self.client.force_login(self.gestor)
        pagina = self.client.get(self.url)
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, "Licenças ativas")
        self.assertEqual(pagina.context["categorias"][0]["nome"], "Vestuário")
        self.assertEqual(pagina.context["licencas_ativas"], 1)
        self.assertEqual(pagina.context["licencas_pendentes"], 0)
        self.assertEqual(pagina.context["ocorrencias_periodo"], 1)

        brasil = self.client.get(self.url, {"bairro": "Brasil"})
        self.assertEqual(brasil.context["licencas_ativas"], 1)
        ocupacao_brasil = {item["bairro"]: item for item in brasil.context["ocupacao"]}
        self.assertEqual(ocupacao_brasil["Brasil"]["total"], 2)
        self.assertEqual(ocupacao_brasil["Brasil"]["ocupados"], 1)
        self.assertEqual(ocupacao_brasil["Brasil"]["percentual"], 50.0)
        self.assertNotIn("Centro", ocupacao_brasil)

        centro = self.client.get(self.url, {"bairro": "Centro"})
        self.assertEqual(centro.context["licencas_ativas"], 0)
        ocupacao_centro = {item["bairro"]: item for item in centro.context["ocupacao"]}
        self.assertEqual(ocupacao_centro["Centro"]["ocupados"], 0)

    def test_api_json_bate_com_o_banco_e_htmx_devolve_html(self):
        self._emitir()
        self.client.force_login(self.gestor)
        api = self.client.get(self.url_api, {"bairro": "Brasil"})
        self.assertEqual(api.status_code, 200)
        payload = json.loads(api.content)
        self.assertEqual(payload["licencas"]["ativas"], 1)
        self.assertEqual(payload["ocupacao"][0]["bairro"], "Brasil")
        self.assertEqual(payload["ocupacao"][0]["ocupados"], 1)
        self.assertEqual(payload["categorias"][0]["nome"], "Vestuário")

        htmx = self.client.get(
            self.url_api,
            {"bairro": "Brasil", "formato": "html"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(htmx.status_code, 200)
        self.assertContains(htmx, "Brasil")
        self.assertContains(htmx, "50")

    def test_filtro_itinerantes_zera_licenca_de_fixo(self):
        self._emitir()
        dados = indicadores_gerenciais(origem="itinerantes")
        self.assertEqual(dados["licencas_ativas"], 0)
        residentes = indicadores_gerenciais(origem="residentes")
        self.assertEqual(residentes["licencas_ativas"], 1)
        self.assertEqual(residentes["residentes"], 1)
