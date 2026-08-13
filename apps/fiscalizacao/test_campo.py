from datetime import datetime, time, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.core.qrcode import validar_codigo_qr
from apps.espacos.models import (
    Endereco,
    EstruturaTrabalho,
    PontoOcupacao,
    StatusOcupacao,
)
from apps.fiscalizacao.models import OcorrenciaInspecao, TipoOcorrencia
from apps.fiscalizacao.services import (
    consultar_campo,
    esta_fora_do_horario,
    inspecionar_qr,
)
from apps.licenciamento.models import CategoriaProduto, StatusLicenca
from apps.licenciamento.services import abrir_requerimento, emitir_alvara
from apps.usuarios.tests import UsuariosAuthFixtures


class FiscalizacaoCampoTests(UsuariosAuthFixtures, TestCase):
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
        self.url = reverse("fiscal_painel")
        self.url_ocorrencia = reverse("fiscal_ocorrencia")

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

    def test_anonimo_vai_ao_login_fiscal(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("fiscal_entrar"), response.url)

    def test_ambulante_nao_acessa_fiscalizacao(self):
        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("ambulante_painel"))

    def test_qr_valido_mostra_ficha_do_alvara(self):
        self._emitir()
        self.licenca.refresh_from_db()
        self.ambulante.refresh_from_db()
        self.client.force_login(self.fiscal)

        response = self.client.get(self.url, {"qr": self.ambulante.codigo_qr_code})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ambulante.nome_completo)
        self.assertContains(response, self.licenca.numero_licenca)
        self.assertContains(response, "Feira do Bairro Brasil")
        self.assertContains(response, "06:00")
        self.assertContains(response, reverse("fiscal_ocorrencia"))
        self.assertEqual(validar_codigo_qr(self.ambulante.codigo_qr_code), self.licenca)

    def test_busca_manual_por_cpf_e_alvara(self):
        self._emitir()
        self.licenca.refresh_from_db()
        self.client.force_login(self.fiscal)

        por_cpf = self.client.get(self.url, {"q": self.ambulante.cpf})
        self.assertContains(por_cpf, self.licenca.numero_licenca)

        por_alvara = self.client.get(self.url, {"q": self.licenca.numero_licenca})
        self.assertContains(por_alvara, "João Ambulante")

    def test_qr_adulterado_nao_mostra_ficha_e_oferece_ocorrencia(self):
        self.client.force_login(self.fiscal)
        response = self.client.get(self.url, {"qr": "codigo-adulterado"})
        self.assertContains(response, "inválido ou adulterado")
        self.assertContains(response, reverse("fiscal_ocorrencia"))
        self.assertNotContains(response, 'id="ficha-inspecao"')

    def test_suspensa_mostra_ficha_irregular(self):
        self._emitir()
        self.licenca.status = StatusLicenca.SUSPENSO
        self.licenca.save(update_fields=["status"])
        self.ambulante.refresh_from_db()
        self.client.force_login(self.fiscal)

        response = self.client.get(self.url, {"qr": self.ambulante.codigo_qr_code})
        self.assertContains(response, "suspensa")
        self.assertContains(response, "Registrar ocorrência")
        self.assertIsNone(validar_codigo_qr(self.ambulante.codigo_qr_code))

    def test_fora_do_horario_na_escala(self):
        self._emitir()
        domingo = datetime(2026, 8, 16, 10, 0, tzinfo=dt_timezone.utc)
        segunda = datetime(2026, 8, 17, 10, 0, tzinfo=dt_timezone.utc)
        self.assertTrue(esta_fora_do_horario(self.licenca, domingo))
        self.assertFalse(esta_fora_do_horario(self.licenca, segunda))

    def test_registra_ocorrencia_com_evidencia(self):
        self._emitir()
        self.licenca.refresh_from_db()
        self.client.force_login(self.fiscal)
        buffer = BytesIO()
        Image.new("RGB", (4, 4), color="red").save(buffer, format="PNG")
        foto = SimpleUploadedFile(
            "evidencia.png",
            buffer.getvalue(),
            content_type="image/png",
        )
        response = self.client.post(
            f"{self.url_ocorrencia}?ambulante={self.ambulante.pk}",
            {
                "ambulante_id": self.ambulante.pk,
                "identificacao": self.licenca.numero_licenca,
                "local_ocorrencia": "Feira do Bairro Brasil",
                "tipo_ocorrencia": TipoOcorrencia.FORA_HORARIO,
                "descricao": "Ambulante fora do horário da escala.",
                "evidencia_foto": foto,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        ocorrencia = OcorrenciaInspecao.objects.get()
        self.assertEqual(ocorrencia.fiscal_id, self.fiscal.pk)
        self.assertEqual(ocorrencia.ambulante_id, self.ambulante.pk)
        self.assertEqual(ocorrencia.tipo_ocorrencia, TipoOcorrencia.FORA_HORARIO)
        self.assertEqual(ocorrencia.status_ocorrencia, "Registrada")
        self.assertTrue(ocorrencia.evidencia_foto)

        self.client.logout()
        self.client.force_login(self.gestor)
        lista = self.client.get(reverse("gestor_ocorrencias"))
        self.assertContains(lista, "João Ambulante")
        self.assertContains(lista, "Irregularidade de horário")

    def test_inspecionar_qr_bate_com_item_8(self):
        self._emitir()
        self.ambulante.refresh_from_db()
        resultado = inspecionar_qr(self.ambulante.codigo_qr_code)
        self.assertEqual(resultado.licenca, self.licenca)
        self.assertEqual(
            consultar_campo(self.ambulante.codigo_qr_code).ambulante, self.ambulante
        )
        self.assertEqual(inspecionar_qr("x" * 64).motivo, "adulterado")
