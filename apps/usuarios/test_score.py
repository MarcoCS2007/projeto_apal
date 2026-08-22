from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.espacos.models import (
    Endereco,
    EstruturaTrabalho,
    PontoOcupacao,
    StatusOcupacao,
)
from apps.fiscalizacao.models import StatusOcorrencia, TipoOcorrencia
from apps.fiscalizacao.services import auditar_ocorrencia, registrar_ocorrencia
from apps.licenciamento.models import CategoriaProduto, StatusLicenca
from apps.licenciamento.services import abrir_requerimento, emitir_alvara
from apps.usuarios.models import EventoScore
from apps.usuarios.tests import UsuariosAuthFixtures


class ScoreAmbulanteTests(UsuariosAuthFixtures, TestCase):
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
        self.url = reverse("ambulante_score")

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

    def _emitir(self):
        hoje = timezone.localdate()
        return emitir_alvara(
            self.licenca,
            self.gestor,
            data_emissao=hoje,
            data_vencimento=hoje + timedelta(days=365),
            ponto=self.ponto,
            dias_semana=["segunda", "terca", "quarta", "quinta", "sexta"],
            horario_inicio=time(6, 0),
            horario_termino=time(18, 0),
        )

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_anonimo_vai_ao_entrar(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("entrar"), response.url)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_ocorrencia_procedente_reduz_score_na_tela_e_no_dossie(self):
        self._emitir()
        self.assertEqual(self.ambulante.pontuacao, 100)
        ocorrencia = registrar_ocorrencia(
            self.fiscal,
            self.ambulante,
            TipoOcorrencia.ADVERTENCIA,
            "Uso irregular da calçada.",
            local_ocorrencia="Feira do Bairro Brasil",
        )
        auditar_ocorrencia(ocorrencia, StatusOcorrencia.PROCEDENTE)
        self.ambulante.refresh_from_db()
        self.assertLess(self.ambulante.pontuacao, 100)
        self.assertTrue(
            EventoScore.objects.filter(
                ambulante=self.ambulante,
                tipo="ocorrencia_procedente",
            ).exists()
        )

        self.client.force_login(self.ambulante)
        score = self.client.get(self.url)
        self.assertEqual(score.status_code, 200)
        self.assertContains(score, str(self.ambulante.pontuacao))
        self.assertContains(score, "Ocorrência")
        self.assertContains(score, "Histórico de pontuação")

        self.client.logout()
        self.client.force_login(self.gestor)
        dossie = self.client.get(reverse("gestor_dossie", args=[self.ambulante.pk]))
        self.assertContains(dossie, str(self.ambulante.pontuacao))
        self.assertContains(dossie, "Histórico de score")
        self.assertContains(dossie, "procedente")
