from datetime import time, timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.espacos.models import (
    Endereco,
    EstruturaTrabalho,
    PontoOcupacao,
    StatusOcupacao,
)
from apps.fiscalizacao.models import StatusOcorrencia, TipoOcorrencia
from apps.fiscalizacao.services import (
    auditar_ocorrencia,
    filtrar_ocorrencias,
    registrar_ocorrencia,
)
from apps.licenciamento.models import CategoriaProduto, StatusLicenca
from apps.licenciamento.services import abrir_requerimento, emitir_alvara
from apps.usuarios.tests import UsuariosAuthFixtures


class AuditoriaOcorrenciaTests(UsuariosAuthFixtures, TestCase):
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
        self._emitir()
        self.licenca.refresh_from_db()
        self.ocorrencia = registrar_ocorrencia(
            self.fiscal,
            self.ambulante,
            TipoOcorrencia.FORA_HORARIO,
            "Ambulante fora do horário da escala.",
            local_ocorrencia="Feira do Bairro Brasil",
            evidencia_foto=self._foto(),
        )
        self.url_lista = reverse("gestor_ocorrencias")
        self.url_detalhe = reverse(
            "gestor_ocorrencia_detalhe", args=[self.ocorrencia.pk]
        )

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

    def _foto(self):
        buffer = BytesIO()
        Image.new("RGB", (4, 4), color="red").save(buffer, format="PNG")
        return SimpleUploadedFile(
            "evidencia.png",
            buffer.getvalue(),
            content_type="image/png",
        )

    def test_fiscal_nao_acessa_auditoria(self):
        self.client.force_login(self.fiscal)
        response = self.client.get(self.url_lista)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("fiscal_painel"))

    def test_gestor_lista_e_filtra_ocorrencia_do_item_10(self):
        self.client.force_login(self.gestor)
        lista = self.client.get(self.url_lista)
        self.assertContains(lista, "João Ambulante")
        self.assertContains(lista, "Irregularidade de horário")
        self.assertContains(lista, self.url_detalhe)

        filtrada = self.client.get(
            self.url_lista, {"q": "João", "status": "Registrada"}
        )
        self.assertContains(filtrada, "João Ambulante")

        vazia = self.client.get(self.url_lista, {"status": StatusOcorrencia.PROCEDENTE})
        self.assertContains(vazia, "Nenhuma ocorrência lançada ainda.")

        self.assertEqual(filtrar_ocorrencias(q="Feira").count(), 1)
        self.assertEqual(
            filtrar_ocorrencias(tipo=TipoOcorrencia.ADVERTENCIA).count(), 0
        )

    def test_detalhe_mostra_evidencia(self):
        self.client.force_login(self.gestor)
        detalhe = self.client.get(self.url_detalhe)
        self.assertEqual(detalhe.status_code, 200)
        self.assertContains(detalhe, "Evidência fotográfica")
        self.assertContains(detalhe, self.ocorrencia.evidencia_foto.url)
        self.assertContains(detalhe, "Ambulante fora do horário")

    def test_procedente_suspende_licenca_e_some_qr_da_credencial(self):
        self.client.force_login(self.gestor)
        response = self.client.post(
            self.url_detalhe,
            {
                "status_ocorrencia": StatusOcorrencia.PROCEDENTE,
                "acao_licenca": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.ocorrencia.refresh_from_db()
        self.licenca.refresh_from_db()
        self.assertEqual(self.ocorrencia.status_ocorrencia, StatusOcorrencia.PROCEDENTE)
        self.assertEqual(self.licenca.status, StatusLicenca.SUSPENSO)

        self.client.logout()
        self.client.force_login(self.ambulante)
        credencial = self.client.get(reverse("ambulante_credencial"))
        self.assertContains(credencial, "Credencial ainda não disponível")
        self.assertContains(credencial, "suspensa")
        self.assertNotContains(credencial, "data-qr-codigo")
        self.assertEqual(
            self.client.get(reverse("ambulante_credencial_qr")).status_code, 404
        )

        self.client.logout()
        self.client.force_login(self.gestor)
        dossie = self.client.get(reverse("gestor_dossie", args=[self.ambulante.pk]))
        self.assertContains(dossie, "Procedente")
        self.assertContains(dossie, self.url_detalhe)

    def test_improcedente_nao_suspende_licenca(self):
        self.client.force_login(self.gestor)
        self.client.post(
            self.url_detalhe,
            {
                "status_ocorrencia": StatusOcorrencia.IMPROCEDENTE,
                "acao_licenca": "",
            },
        )
        self.ocorrencia.refresh_from_db()
        self.licenca.refresh_from_db()
        self.assertEqual(
            self.ocorrencia.status_ocorrencia, StatusOcorrencia.IMPROCEDENTE
        )
        self.assertEqual(self.licenca.status, StatusLicenca.ATIVO)

    def test_cancelar_a_partir_de_procedente(self):
        auditar_ocorrencia(self.ocorrencia, StatusOcorrencia.PROCEDENTE)
        self.licenca.refresh_from_db()
        self.assertEqual(self.licenca.status, StatusLicenca.SUSPENSO)

        self.client.force_login(self.gestor)
        self.client.post(
            self.url_detalhe,
            {
                "status_ocorrencia": StatusOcorrencia.PROCEDENTE,
                "acao_licenca": "cancelar",
            },
        )
        self.licenca.refresh_from_db()
        self.assertEqual(self.licenca.status, StatusLicenca.CANCELADO)

    def test_transicao_invalida_e_convertida_em_multa(self):
        with self.assertRaises(ValueError):
            auditar_ocorrencia(self.ocorrencia, StatusOcorrencia.CONVERTIDA_MULTA)
        auditar_ocorrencia(self.ocorrencia, StatusOcorrencia.PROCEDENTE)
        auditar_ocorrencia(self.ocorrencia, StatusOcorrencia.CONVERTIDA_MULTA)
        self.ocorrencia.refresh_from_db()
        self.assertEqual(
            self.ocorrencia.status_ocorrencia, StatusOcorrencia.CONVERTIDA_MULTA
        )
