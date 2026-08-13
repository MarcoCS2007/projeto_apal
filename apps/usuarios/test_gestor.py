from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.espacos.models import Endereco, EstruturaTrabalho, PontoOcupacao, StatusOcupacao
from apps.licenciamento.models import (
    CategoriaProduto,
    StatusLicenca,
    TipoDocumento,
)
from apps.licenciamento.services import abrir_requerimento, registrar_documento
from apps.usuarios.tests import UsuariosAuthFixtures


class PainelGestorTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.categoria = CategoriaProduto.objects.create(
            nome_categoria="Alimentos Manipulados",
            descricao="Alimentos preparados na hora.",
            exige_laudo_sanitario=True,
        )
        self.ponto = PontoOcupacao.objects.create(
            nome_identificacao="Praça Central",
            logradouro="Praça Barão do Rio Branco",
            bairro="Centro",
            metragem_maxima=Decimal("10.00"),
            status_ocupacao=StatusOcupacao.LIVRE,
        )
        self._completar(self.ambulante)
        self.licenca, _criado = abrir_requerimento(self.ambulante, self.categoria)

    def _completar(self, ambulante):
        ambulante.tipo_atuacao = "fixo"
        ambulante.ponto_pretendido = self.ponto
        extras = dict(ambulante.dados_complementares or {})
        extras["categoria_id"] = self.categoria.pk
        ambulante.dados_complementares = extras
        ambulante.save()
        if not ambulante.enderecos.exists():
            Endereco.objects.create(
                ambulante=ambulante,
                cep="45000-000",
                logradouro="Rua A",
                numero="10",
                bairro="Centro",
                cidade="Vitória da Conquista",
                estado_uf="BA",
            )
        if not ambulante.estruturas.exists():
            EstruturaTrabalho.objects.create(
                ambulante=ambulante,
                tipo_estrutura="carrinho",
                dimensoes_metragem=Decimal("2.50"),
                descricao="Lanches",
            )

    def test_ambulante_nao_acessa_fila(self):
        self.client.force_login(self.ambulante)
        response = self.client.get(reverse("gestor_fila"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("ambulante_painel"))

    def test_gestor_abre_fila_com_requerimento(self):
        self.client.force_login(self.gestor)
        response = self.client.get(reverse("gestor_fila"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.licenca.protocolo)
        self.assertContains(response, "João Ambulante")
        self.assertContains(response, reverse("gestor_analisar", args=[self.licenca.pk]))

    def test_dossie_mostra_dados_e_score(self):
        self.client.force_login(self.gestor)
        response = self.client.get(reverse("gestor_dossie", args=[self.ambulante.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "João Ambulante")
        self.assertContains(response, str(self.ambulante.pontuacao))
        self.assertContains(response, self.licenca.protocolo)
        from apps.usuarios.models import LogAcessoDossie

        self.assertTrue(
            LogAcessoDossie.objects.filter(
                usuario=self.gestor, ambulante=self.ambulante
            ).exists()
        )

    def test_indeferir_com_motivo(self):
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse("gestor_analisar", args=[self.licenca.pk]),
            {
                "acao": "indeferir",
                "motivo": "Documentação incompleta para a categoria de alimentos.",
                "categoria_produto": self.categoria.pk,
                "ponto_ocupacao": self.ponto.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("gestor_fila"))
        self.licenca.refresh_from_db()
        self.assertEqual(self.licenca.status, StatusLicenca.INDEFERIDO)
        self.assertIn("Documentação incompleta", self.licenca.motivo_parecer)
        fila = self.client.get(reverse("gestor_fila"))
        self.assertNotContains(fila, self.licenca.protocolo)

    def test_indeferir_sem_motivo_e_recusado(self):
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse("gestor_analisar", args=[self.licenca.pk]),
            {
                "acao": "indeferir",
                "motivo": "",
                "categoria_produto": self.categoria.pk,
                "ponto_ocupacao": self.ponto.pk,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.licenca.refresh_from_db()
        self.assertEqual(self.licenca.status, StatusLicenca.EM_ANALISE)

    def _aprovar_documentos_obrigatorios(self):
        for tipo in (
            TipoDocumento.COMPROVANTE_RESIDENCIA,
            TipoDocumento.RG_CPF,
            TipoDocumento.LAUDO_SANITARIO,
        ):
            arquivo = SimpleUploadedFile(
                f"{tipo}.pdf",
                b"%PDF-1.4 teste",
                content_type="application/pdf",
            )
            documento = registrar_documento(self.ambulante, tipo, arquivo)
            documento.aprovar()

    def test_deferir_encaminha_para_emissao(self):
        self._aprovar_documentos_obrigatorios()
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse("gestor_analisar", args=[self.licenca.pk]),
            {
                "acao": "deferir",
                "categoria_produto": self.categoria.pk,
                "ponto_ocupacao": self.ponto.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, reverse("gestor_emitir", args=[self.licenca.pk])
        )
        self.licenca.refresh_from_db()
        self.assertEqual(self.licenca.status, StatusLicenca.APROVADO)
        self.assertEqual(self.licenca.gestor_responsavel_id, self.gestor.pk)
        self.assertIsNone(self.licenca.numero_licenca)

    def test_devolver_com_pendencia(self):
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse("gestor_analisar", args=[self.licenca.pk]),
            {
                "acao": "pendencia",
                "motivo": "Anexar laudo sanitário atualizado.",
                "categoria_produto": self.categoria.pk,
                "ponto_ocupacao": self.ponto.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.licenca.refresh_from_db()
        self.assertEqual(self.licenca.status, StatusLicenca.PENDENCIA_DOCUMENTAL)
        fila = self.client.get(reverse("gestor_fila"))
        self.assertContains(fila, self.licenca.protocolo)
        self.assertContains(fila, "Pendência Documental")

    def test_editar_e_suspender_ambulante(self):
        self.client.force_login(self.gestor)
        editar = self.client.post(
            reverse("gestor_ambulante_editar", args=[self.ambulante.pk]),
            {
                "nome_completo": "João da Silva Santos",
                "email": self.ambulante.email,
                "telefone_whatsapp": "77999999999",
                "tipo_atuacao": "fixo",
            },
        )
        self.assertEqual(editar.status_code, 302)
        self.ambulante.refresh_from_db()
        self.assertEqual(self.ambulante.nome_completo, "João da Silva Santos")

        suspender = self.client.post(
            reverse("gestor_ambulante_acao", args=[self.ambulante.pk]),
            {"acao": "suspender"},
        )
        self.assertEqual(suspender.status_code, 302)
        self.ambulante.refresh_from_db()
        self.assertEqual(self.ambulante.situacao_conta, "suspensa")
