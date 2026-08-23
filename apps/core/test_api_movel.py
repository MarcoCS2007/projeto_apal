import tempfile
from datetime import time, timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.espacos.models import (
    Endereco,
    EstruturaTrabalho,
    PontoOcupacao,
    StatusOcupacao,
)
from apps.fiscalizacao.models import OcorrenciaInspecao, TipoOcorrencia
from apps.licenciamento.models import CategoriaProduto, StatusLicenca, TipoDocumento
from apps.licenciamento.services import abrir_requerimento, emitir_alvara
from apps.usuarios.tests import UsuariosAuthFixtures


class LocaleProdutoTests(SimpleTestCase):
    def test_idioma_e_fuso_de_vitoria_da_conquista(self):
        self.assertEqual(settings.LANGUAGE_CODE, "pt-br")
        self.assertEqual(settings.TIME_ZONE, "America/Bahia")


class ApiMovelTests(UsuariosAuthFixtures, APITestCase):
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

    def _emitir(self):
        hoje = timezone.localdate()
        return emitir_alvara(
            self.licenca,
            self.gestor,
            data_emissao=hoje,
            data_vencimento=hoje + timedelta(days=365),
            ponto=self.ponto,
            dias_semana=[
                "segunda",
                "terca",
                "quarta",
                "quinta",
                "sexta",
                "sabado",
                "domingo",
            ],
            horario_inicio=time(0, 0),
            horario_termino=time(23, 59),
        )

    def _token(self, user):
        login = self.client.post(
            reverse("api_login"),
            {"cpf": user.cpf, "password": self.senha},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        return login.data["access"]

    def _auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._token(user)}")

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_anonimo_recebe_401_nas_rotas_protegidas(self):
        for nome in (
            "api_ambulante_solicitacao",
            "api_fiscal_qr",
            "api_ambulante_score",
        ):
            with self.subTest(nome=nome):
                response = self.client.get(reverse(nome))
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_login_ambulante_consulta_status_da_licenca(self):
        self._auth(self.ambulante)
        response = self.client.get(reverse("api_ambulante_solicitacao"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["licenca"]["protocolo"], self.licenca.protocolo)
        self.assertEqual(response.data["licenca"]["status"], StatusLicenca.APROVADO)

        cadastro = self.client.get(reverse("api_ambulante_cadastro"))
        self.assertEqual(cadastro.status_code, status.HTTP_200_OK)
        self.assertTrue(cadastro.data["cadastro_completo"])
        self.assertEqual(cadastro.data["cpf"], self.ambulante.cpf)

        score = self.client.get(reverse("api_ambulante_score"))
        self.assertEqual(score.status_code, status.HTTP_200_OK)
        self.assertIn("pontuacao", score.data)
        self.assertIn("faixa", score.data)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_fiscal_nao_acessa_rotas_do_ambulante(self):
        self._auth(self.fiscal)
        response = self.client.get(reverse("api_ambulante_solicitacao"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_login_fiscal_valida_qr_e_registra_ocorrencia(self):
        self._emitir()
        self.ambulante.refresh_from_db()
        self.licenca.refresh_from_db()
        self._auth(self.fiscal)

        sem_codigo = self.client.get(reverse("api_fiscal_qr"))
        self.assertEqual(sem_codigo.status_code, status.HTTP_400_BAD_REQUEST)

        adulterado = self.client.get(reverse("api_fiscal_qr"), {"codigo": "x" * 64})
        self.assertEqual(adulterado.status_code, status.HTTP_200_OK)
        self.assertFalse(adulterado.data["valido"])
        self.assertEqual(adulterado.data["motivo"], "adulterado")

        qr = self.client.get(
            reverse("api_fiscal_qr"), {"codigo": self.ambulante.codigo_qr_code}
        )
        self.assertEqual(qr.status_code, status.HTTP_200_OK)
        self.assertTrue(qr.data["valido"])
        self.assertEqual(
            qr.data["licenca"]["numero_licenca"], self.licenca.numero_licenca
        )
        self.assertEqual(qr.data["ambulante"]["id"], self.ambulante.pk)

        busca = self.client.get(reverse("api_fiscal_busca"), {"q": self.ambulante.cpf})
        self.assertEqual(busca.status_code, status.HTTP_200_OK)
        self.assertEqual(
            busca.data["licenca"]["numero_licenca"], self.licenca.numero_licenca
        )

        buffer = BytesIO()
        Image.new("RGB", (4, 4), color="red").save(buffer, format="PNG")
        foto = SimpleUploadedFile(
            "evidencia.png", buffer.getvalue(), content_type="image/png"
        )
        ocorrencia = self.client.post(
            reverse("api_fiscal_ocorrencias"),
            {
                "ambulante_id": self.ambulante.pk,
                "local_ocorrencia": "Feira do Bairro Brasil",
                "tipo_ocorrencia": TipoOcorrencia.FORA_HORARIO,
                "descricao": "Ambulante fora do horário da escala.",
                "evidencia_foto": foto,
            },
        )
        self.assertEqual(ocorrencia.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ocorrencia.data["status_ocorrencia"], "Registrada")
        self.assertTrue(ocorrencia.data["tem_evidencia"])
        self.assertEqual(OcorrenciaInspecao.objects.count(), 1)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_ambulante_nao_registra_ocorrencia(self):
        self._auth(self.ambulante)
        response = self.client.post(
            reverse("api_fiscal_ocorrencias"),
            {
                "local_ocorrencia": "Centro",
                "tipo_ocorrencia": TipoOcorrencia.ADVERTENCIA,
                "descricao": "Tentativa indevida.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_credencial_documentos_e_assistente(self):
        self._emitir()
        self.ambulante.refresh_from_db()
        self._auth(self.ambulante)

        credencial = self.client.get(reverse("api_ambulante_credencial"))
        self.assertEqual(credencial.status_code, status.HTTP_200_OK)
        self.assertTrue(credencial.data["qr_liberado"])
        self.assertEqual(credencial.data["codigo_qr"], self.ambulante.codigo_qr_code)

        png = self.client.get(reverse("api_ambulante_credencial_qr"))
        self.assertEqual(png.status_code, status.HTTP_200_OK)
        self.assertEqual(png["Content-Type"], "image/png")

        documentos = self.client.get(reverse("api_ambulante_documentos"))
        self.assertEqual(documentos.status_code, status.HTTP_200_OK)
        self.assertIn("documentos", documentos.data)

        with (
            tempfile.TemporaryDirectory() as tmp,
            override_settings(MEDIA_ROOT=tmp),
        ):
            pdf = SimpleUploadedFile(
                "rg.pdf", b"%PDF-1.4 teste", content_type="application/pdf"
            )
            envio = self.client.post(
                reverse("api_ambulante_documentos"),
                {"tipo_documento": TipoDocumento.RG_CPF, "arquivo": pdf},
            )
            self.assertEqual(envio.status_code, status.HTTP_201_CREATED)
            self.assertEqual(envio.data["tipo"], TipoDocumento.RG_CPF)

        chat = self.client.post(
            reverse("api_ambulante_assistente"),
            {"pergunta": "quais os prazos de renovação?"},
            format="json",
        )
        self.assertEqual(chat.status_code, status.HTTP_201_CREATED)
        self.assertIn("31 de dezembro", chat.data["resposta"])

        historico = self.client.get(reverse("api_ambulante_assistente"))
        self.assertEqual(historico.status_code, status.HTTP_200_OK)
        self.assertEqual(len(historico.data["historico"]), 1)
