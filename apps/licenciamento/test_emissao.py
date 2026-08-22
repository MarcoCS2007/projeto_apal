from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.qrcode import gerar_codigo_qr, validar_codigo_qr
from apps.espacos.models import (
    Endereco,
    EstruturaTrabalho,
    PontoOcupacao,
    StatusOcupacao,
)
from apps.licenciamento.models import (
    CategoriaProduto,
    EscalaTrabalho,
    LicencaAlvara,
    StatusLicenca,
)
from apps.licenciamento.services import abrir_requerimento, marcar_licencas_vencidas
from apps.usuarios.tests import UsuariosAuthFixtures


class EmissaoAlvaraTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.categoria = CategoriaProduto.objects.create(
            nome_categoria="Vestuário",
            descricao="Roupas e acessórios.",
        )
        self.ponto = PontoOcupacao.objects.create(
            nome_identificacao="Feira do Bairro Brasil",
            logradouro="Rua da Feira",
            bairro="Brasil",
            metragem_maxima=Decimal("12.00"),
            status_ocupacao=StatusOcupacao.LIVRE,
        )
        self._completar(self.ambulante)
        self.licenca, _criado = abrir_requerimento(self.ambulante, self.categoria)
        self.licenca.status = StatusLicenca.APROVADO
        self.licenca.ponto_ocupacao = self.ponto
        self.licenca.categoria_produto = self.categoria
        self.licenca.save()

    def _completar(self, ambulante):
        ambulante.tipo_atuacao = "fixo"
        ambulante.ponto_pretendido = self.ponto
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

    def _payload(self, **extra):
        hoje = timezone.localdate()
        dados = {
            "data_emissao": hoje.isoformat(),
            "data_vencimento": (hoje + timedelta(days=365)).isoformat(),
            "ponto_ocupacao": self.ponto.pk,
            "dias_semana": ["segunda", "terca", "quarta", "quinta", "sexta"],
            "horario_inicio": "06:00",
            "horario_termino": "18:00",
        }
        dados.update(extra)
        return dados

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_ambulante_nao_acessa_emissao(self):
        self.client.force_login(self.ambulante)
        response = self.client.get(reverse("gestor_emitir", args=[self.licenca.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("ambulante_painel"))

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_gestor_abre_tela_de_emissao(self):
        self.client.force_login(self.gestor)
        response = self.client.get(reverse("gestor_emitir", args=[self.licenca.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.licenca.protocolo)
        self.assertContains(response, "Feira do Bairro Brasil")
        self.assertContains(response, "Emitir alvará e gerar QR Code")

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_emitir_gera_numero_ocupa_ponto_escala_e_qr(self):
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse("gestor_emitir", args=[self.licenca.pk]),
            self._payload(),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("gestor_licencas"))

        self.licenca.refresh_from_db()
        self.ambulante.refresh_from_db()
        self.ponto.refresh_from_db()

        self.assertEqual(self.licenca.status, StatusLicenca.ATIVO)
        self.assertTrue(self.licenca.numero_licenca.startswith("ALV-"))
        self.assertEqual(self.ponto.status_ocupacao, StatusOcupacao.OCUPADO)
        self.assertEqual(self.licenca.escalas.count(), 5)
        self.assertTrue(
            EscalaTrabalho.objects.filter(
                licenca_alvara=self.licenca,
                dia_semana="segunda",
                horario_inicio=time(6, 0),
                horario_termino=time(18, 0),
            ).exists()
        )
        self.assertEqual(self.ambulante.codigo_qr_code, gerar_codigo_qr(self.licenca))
        self.assertEqual(validar_codigo_qr(self.ambulante.codigo_qr_code), self.licenca)

        lista = self.client.get(reverse("gestor_licencas"))
        self.assertContains(lista, self.licenca.numero_licenca)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_qr_invalido_se_suspenso_ou_adulterado(self):
        self.client.force_login(self.gestor)
        self.client.post(
            reverse("gestor_emitir", args=[self.licenca.pk]), self._payload()
        )
        self.ambulante.refresh_from_db()
        codigo = self.ambulante.codigo_qr_code

        self.assertIsNone(validar_codigo_qr("codigo-adulterado"))
        self.licenca.status = StatusLicenca.SUSPENSO
        self.licenca.save(update_fields=["status"])
        self.assertIsNone(validar_codigo_qr(codigo))

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_consulta_marca_licenca_vencida_e_libera_ponto(self):
        self.client.force_login(self.gestor)
        self.client.post(
            reverse("gestor_emitir", args=[self.licenca.pk]), self._payload()
        )
        self.licenca.refresh_from_db()
        self.licenca.data_vencimento = timezone.localdate() - timedelta(days=1)
        self.licenca.save(update_fields=["data_vencimento"])

        self.assertEqual(marcar_licencas_vencidas(), 1)
        self.licenca.refresh_from_db()
        self.ponto.refresh_from_db()
        self.ambulante.refresh_from_db()
        self.assertEqual(self.licenca.status, StatusLicenca.VENCIDO)
        self.assertEqual(self.ponto.status_ocupacao, StatusOcupacao.LIVRE)
        self.assertIsNone(validar_codigo_qr(self.ambulante.codigo_qr_code))

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_nao_emite_duas_vezes(self):
        self.client.force_login(self.gestor)
        primeira = self.client.post(
            reverse("gestor_emitir", args=[self.licenca.pk]),
            self._payload(),
        )
        self.assertEqual(primeira.status_code, 302)
        segunda = self.client.post(
            reverse("gestor_emitir", args=[self.licenca.pk]),
            self._payload(),
        )
        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(
            LicencaAlvara.objects.filter(numero_licenca__isnull=False).count(), 1
        )

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_filtro_por_status_e_vencimento_proximo(self):
        self.client.force_login(self.gestor)
        self.client.post(
            reverse("gestor_emitir", args=[self.licenca.pk]), self._payload()
        )
        self.licenca.refresh_from_db()

        ativas = self.client.get(reverse("gestor_licencas"), {"status": "Ativo"})
        self.assertContains(ativas, self.licenca.numero_licenca)

        vencidas = self.client.get(reverse("gestor_licencas"), {"status": "Vencido"})
        self.assertNotContains(vencidas, self.licenca.numero_licenca)

        self.licenca.data_vencimento = timezone.localdate() + timedelta(days=10)
        self.licenca.save(update_fields=["data_vencimento"])
        proximas = self.client.get(
            reverse("gestor_licencas"), {"vencimento_proximo": "1"}
        )
        self.assertContains(proximas, self.licenca.numero_licenca)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_qr_e_estavel_para_a_mesma_licenca(self):
        self.licenca.numero_licenca = "ALV-2026-0001"
        primeiro = gerar_codigo_qr(self.licenca)
        segundo = gerar_codigo_qr(self.licenca)
        self.assertEqual(primeiro, segundo)
        self.assertEqual(len(primeiro), 64)
