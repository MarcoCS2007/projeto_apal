from datetime import time, timedelta
from decimal import Decimal

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
from apps.licenciamento.models import CategoriaProduto, StatusLicenca
from apps.licenciamento.services import abrir_requerimento, emitir_alvara
from apps.usuarios.tests import UsuariosAuthFixtures


class CredencialAmbulanteTests(UsuariosAuthFixtures, TestCase):
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
        self.ambulante.apelido_nome_fantasia = "Barraca do João"
        self._completar(self.ambulante)
        self.licenca, _criado = abrir_requerimento(self.ambulante, self.categoria)
        self.licenca.status = StatusLicenca.APROVADO
        self.licenca.ponto_ocupacao = self.ponto
        self.licenca.categoria_produto = self.categoria
        self.licenca.save()
        self.url = reverse("ambulante_credencial")
        self.url_qr = reverse("ambulante_credencial_qr")

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

    def test_anonimo_e_redirecionado_ao_entrar(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("entrar"), response.url)

    def test_gestor_nao_acessa_credencial(self):
        self.client.force_login(self.gestor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backoffice_inicio"))

    def test_sem_licenca_ativa_nao_mostra_qr(self):
        self.licenca.status = StatusLicenca.EM_ANALISE
        self.licenca.save(update_fields=["status"])
        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Credencial ainda não disponível")
        self.assertContains(response, self.licenca.protocolo)
        self.assertContains(response, "Em Análise")
        self.assertNotContains(response, "data-qr-codigo")
        self.assertNotContains(response, self.url_qr)

        qr = self.client.get(self.url_qr)
        self.assertEqual(qr.status_code, 404)

    def test_credencial_ativa_mostra_dados_e_qr_do_alvara(self):
        self._emitir()
        self.licenca.refresh_from_db()
        self.ambulante.refresh_from_db()

        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "João Ambulante")
        self.assertContains(response, "Barraca do João")
        self.assertContains(response, self.licenca.numero_licenca)
        self.assertContains(response, "Feira do Bairro Brasil")
        self.assertContains(response, "06:00")
        self.assertContains(response, "18:00")
        self.assertContains(response, "Ativo")
        self.assertContains(response, self.ambulante.codigo_qr_code)
        self.assertContains(response, self.url_qr)
        self.assertEqual(validar_codigo_qr(self.ambulante.codigo_qr_code), self.licenca)
        self.assertEqual(self.ambulante.codigo_qr_code, gerar_codigo_qr(self.licenca))

        png = self.client.get(self.url_qr)
        self.assertEqual(png.status_code, 200)
        self.assertEqual(png["Content-Type"], "image/png")
        self.assertTrue(png.content.startswith(b"\x89PNG"))

        baixar = self.client.get(self.url_qr, {"download": "1"})
        self.assertEqual(baixar.status_code, 200)
        self.assertIn("attachment", baixar["Content-Disposition"])
        self.assertIn(self.licenca.numero_licenca, baixar["Content-Disposition"])

    def test_alvara_libera_download_apos_emissao(self):
        self._emitir()
        self.licenca.refresh_from_db()
        self.client.force_login(self.ambulante)

        alvara = self.client.get(reverse("ambulante_alvara"))
        self.assertContains(alvara, "Ver credencial")
        self.assertContains(alvara, self.url)
        self.assertContains(alvara, f"{self.url_qr}?download=1")

        painel = self.client.get(reverse("ambulante_painel"))
        self.assertContains(painel, self.url)
        self.assertContains(painel, "Ver credencial")

    def test_suspensa_nao_mostra_qr_valido(self):
        self._emitir()
        self.licenca.status = StatusLicenca.SUSPENSO
        self.licenca.save(update_fields=["status"])

        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)
        self.assertContains(response, "Credencial ainda não disponível")
        self.assertContains(response, "suspensa")
        self.assertNotContains(response, "data-qr-codigo")
        self.assertEqual(self.client.get(self.url_qr).status_code, 404)

    def test_vencida_nao_mostra_qr_valido(self):
        self._emitir()
        self.licenca.data_vencimento = timezone.localdate() - timedelta(days=1)
        self.licenca.save(update_fields=["data_vencimento"])

        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)
        self.assertContains(response, "Credencial ainda não disponível")
        self.assertContains(response, "venceu")
        self.assertNotContains(response, "data-qr-codigo")
        self.assertEqual(self.client.get(self.url_qr).status_code, 404)
