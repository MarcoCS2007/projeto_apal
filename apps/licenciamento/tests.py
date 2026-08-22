import pytest
import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.espacos.models import (
    Endereco,
    EstruturaTrabalho,
    PontoOcupacao,
    StatusOcupacao,
)
from apps.licenciamento.models import (
    CategoriaProduto,
    DocumentoAnexo,
    StatusAprovacaoDocumento,
    StatusLicenca,
    TipoDocumento,
)
from apps.licenciamento.services import (
    abrir_requerimento,
    aplicar_parecer,
    pode_avancar_solicitacao,
    tipos_faltando_aprovacao,
)
from apps.usuarios.tests import UsuariosAuthFixtures


class CatalogoGestorTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.url_categorias = reverse("gestor_categorias")
        self.url_pontos = reverse("gestor_pontos")

    def test_anonimo_e_redirecionado_ao_login(self):
        for url in (self.url_categorias, self.url_pontos):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response.url)

    def test_ambulante_nao_acessa_catalogo_do_gestor(self):
        self.client.force_login(self.ambulante)
        response = self.client.get(self.url_categorias)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("ambulante_painel"))

    def test_gestor_cadastra_categoria_com_laudo_sanitario(self):
        self.client.force_login(self.gestor)
        response = self.client.post(
            self.url_categorias,
            {
                "nome_categoria": "Alimentos Manipulados",
                "descricao": "Alimentos preparados na hora.",
                "exige_laudo_sanitario": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url_categorias)
        categoria = CategoriaProduto.objects.get(nome_categoria="Alimentos Manipulados")
        self.assertTrue(categoria.exige_laudo_sanitario)
        self.assertFalse(categoria.exige_laudo_bombeiros)

        lista = self.client.get(self.url_categorias)
        self.assertContains(lista, "Alimentos Manipulados")
        self.assertContains(lista, "Obrigatório")

    def test_nao_permite_categoria_duplicada(self):
        CategoriaProduto.objects.create(
            nome_categoria="Artesanato",
            descricao="Peças manuais",
        )
        self.client.force_login(self.gestor)
        response = self.client.post(
            self.url_categorias,
            {"nome_categoria": "artesanato", "descricao": "Outra descrição"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Já existe uma categoria com este nome")
        self.assertEqual(
            CategoriaProduto.objects.filter(
                nome_categoria__iexact="artesanato"
            ).count(),
            1,
        )

    def test_editar_e_excluir_categoria(self):
        categoria = CategoriaProduto.objects.create(
            nome_categoria="Bebidas",
            descricao="Sucos",
        )
        self.client.force_login(self.gestor)
        editar = self.client.post(
            reverse("gestor_categorias_editar", args=[categoria.pk]),
            {
                "nome_categoria": "Bebidas e Água de Coco",
                "descricao": "Bebidas não alcoólicas",
                "exige_laudo_sanitario": "on",
            },
        )
        self.assertEqual(editar.status_code, 302)
        categoria.refresh_from_db()
        self.assertEqual(categoria.nome_categoria, "Bebidas e Água de Coco")
        self.assertTrue(categoria.exige_laudo_sanitario)

        excluir = self.client.post(
            reverse("gestor_categorias_excluir", args=[categoria.pk])
        )
        self.assertEqual(excluir.status_code, 302)
        categoria.refresh_from_db()
        self.assertFalse(categoria.ativo)
        lista = self.client.get(self.url_categorias)
        self.assertNotContains(lista, "Bebidas e Água de Coco")

    def test_gestor_cadastra_ponto_livre(self):
        self.client.force_login(self.gestor)
        response = self.client.post(
            self.url_pontos,
            {
                "nome_identificacao": "Praça Central",
                "logradouro": "Praça Barão do Rio Branco",
                "bairro": "Centro",
                "coordenadas": "-14.8661,-40.8390",
                "metragem_maxima": "10.00",
                "status_ocupacao": StatusOcupacao.LIVRE,
            },
        )

        self.assertEqual(response.status_code, 302)
        ponto = PontoOcupacao.objects.get(nome_identificacao="Praça Central")
        self.assertEqual(ponto.status_ocupacao, StatusOcupacao.LIVRE)
        self.assertEqual(ponto.metragem_maxima, Decimal("10.00"))

        lista = self.client.get(self.url_pontos)
        self.assertContains(lista, "Praça Central")
        self.assertContains(lista, "Livre")


class CatalogoNoCadastroAmbulanteTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.url_cadastro = reverse("ambulante_cadastro")
        self.categoria = CategoriaProduto.objects.create(
            nome_categoria="Alimentos Manipulados",
            descricao="Alimentos preparados na hora.",
            exige_laudo_sanitario=True,
        )
        self.ponto_livre = PontoOcupacao.objects.create(
            nome_identificacao="Praça Central",
            logradouro="Praça Central",
            bairro="Centro",
            metragem_maxima=Decimal("10.00"),
            status_ocupacao=StatusOcupacao.LIVRE,
        )
        self.ponto_ocupado = PontoOcupacao.objects.create(
            nome_identificacao="Calçadão Ocupado",
            logradouro="Rua do Comércio",
            bairro="Centro",
            metragem_maxima=Decimal("15.00"),
            status_ocupacao=StatusOcupacao.OCUPADO,
        )

    def test_formulario_lista_categoria_e_ponto_livre(self):
        self.client.force_login(self.ambulante)
        response = self.client.get(self.url_cadastro, {"etapa": 5})

        self.assertContains(response, "Alimentos Manipulados")
        self.assertContains(response, "laudo sanitário")
        self.assertContains(response, "Praça Central")
        self.assertNotContains(response, "Calçadão Ocupado")

    def test_salva_categoria_e_ponto_pretendidos(self):
        self.client.force_login(self.ambulante)
        response = self.client.post(
            self.url_cadastro,
            {
                "etapa": "5",
                "acao": "proxima",
                "categoria_pretendida": self.categoria.pk,
                "ponto_pretendido": self.ponto_livre.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.ambulante.refresh_from_db()
        self.assertEqual(self.ambulante.ponto_pretendido_id, self.ponto_livre.pk)
        self.assertEqual(
            self.ambulante.dados_complementares.get("categoria_id"), self.categoria.pk
        )

    def test_nao_atribui_ponto_ocupado(self):
        self.client.force_login(self.ambulante)
        response = self.client.post(
            self.url_cadastro,
            {
                "etapa": "5",
                "acao": "proxima",
                "categoria_pretendida": self.categoria.pk,
                "ponto_pretendido": self.ponto_ocupado.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.ambulante.refresh_from_db()
        self.assertIsNone(self.ambulante.ponto_pretendido_id)

    def test_rejeita_metragem_maior_que_o_ponto(self):
        EstruturaTrabalho.objects.create(
            ambulante=self.ambulante,
            tipo_estrutura="carrinho",
            dimensoes_metragem=Decimal("12.00"),
            descricao="Lanches",
        )
        self.client.force_login(self.ambulante)
        response = self.client.post(
            self.url_cadastro,
            {
                "etapa": "5",
                "acao": "proxima",
                "categoria_pretendida": self.categoria.pk,
                "ponto_pretendido": self.ponto_livre.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ultrapassa o máximo")
        self.ambulante.refresh_from_db()
        self.assertIsNone(self.ambulante.ponto_pretendido_id)


def _pdf(nome="arquivo.pdf"):
    return SimpleUploadedFile(nome, b"%PDF-1.4 teste", content_type="application/pdf")


class WorkflowDocumentosTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.categoria = CategoriaProduto.objects.create(
            nome_categoria="Alimentos Manipulados",
            descricao="Alimentos preparados na hora.",
            exige_laudo_sanitario=True,
            exige_laudo_bombeiros=True,
        )
        self.ponto = PontoOcupacao.objects.create(
            nome_identificacao="Praça Central",
            logradouro="Praça Central",
            bairro="Centro",
            metragem_maxima=Decimal("10.00"),
            status_ocupacao=StatusOcupacao.LIVRE,
        )
        self.estrutura = EstruturaTrabalho.objects.create(
            ambulante=self.ambulante,
            tipo_estrutura="carrinho",
            dimensoes_metragem=Decimal("2.50"),
            descricao="Lanches",
        )
        Endereco.objects.create(
            ambulante=self.ambulante,
            cep="45000000",
            logradouro="Rua A",
            numero="10",
            bairro="Centro",
            cidade="Vitória da Conquista",
            estado_uf="BA",
        )
        self.ambulante.ponto_pretendido = self.ponto
        self.ambulante.dados_complementares = {
            "categoria_id": self.categoria.pk,
            "categoria_nome": self.categoria.nome_categoria,
        }
        self.ambulante.save()

    def _criar_documento(self, tipo, nome="doc.pdf"):
        return DocumentoAnexo.objects.create(
            ambulante=self.ambulante,
            tipo_documento=tipo,
            arquivo=_pdf(nome),
        )

    def test_ambulante_envia_comprovante(self):
        self.client.force_login(self.ambulante)
        with (
            tempfile.TemporaryDirectory() as tmp,
            override_settings(MEDIA_ROOT=tmp),
        ):
            response = self.client.post(
                reverse("ambulante_cadastro"),
                {
                    "etapa": "6",
                    "acao": "salvar",
                    "arquivo_comprovante_residencia": _pdf("comprovante.pdf"),
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertIn("etapa=6", response.url)
        doc = DocumentoAnexo.objects.get(ambulante=self.ambulante)
        self.assertEqual(doc.tipo_documento, TipoDocumento.COMPROVANTE_RESIDENCIA)
        self.assertEqual(doc.status_aprovacao, StatusAprovacaoDocumento.PENDENTE)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_gestor_aprova_e_rejeita_com_motivo(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            override_settings(MEDIA_ROOT=tmp),
        ):
            comprovante = self._criar_documento(
                TipoDocumento.COMPROVANTE_RESIDENCIA, "comprovante.pdf"
            )
            rg = self._criar_documento(TipoDocumento.RG_CPF, "rg.pdf")
            licenca, _criado = abrir_requerimento(
                self.ambulante, categoria=self.categoria
            )

            self.client.force_login(self.gestor)
            triagem = self.client.get(reverse("gestor_triagem"))
            self.assertEqual(triagem.status_code, 200)
            self.assertContains(triagem, "Comprovante de Residência")
            self.assertContains(triagem, "RG/CPF")

            aprovar = self.client.post(
                reverse("documento_aprovar", args=[comprovante.pk])
            )
            self.assertEqual(aprovar.status_code, 302)
            comprovante.refresh_from_db()
            self.assertEqual(
                comprovante.status_aprovacao, StatusAprovacaoDocumento.APROVADO
            )

            rejeitar_sem_motivo = self.client.post(
                reverse("documento_rejeitar", args=[rg.pk]),
                {"justificativa": ""},
            )
            self.assertEqual(rejeitar_sem_motivo.status_code, 302)
            rg.refresh_from_db()
            self.assertEqual(rg.status_aprovacao, StatusAprovacaoDocumento.PENDENTE)

            rejeitar = self.client.post(
                reverse("documento_rejeitar", args=[rg.pk]),
                {"justificativa": "Documento ilegível."},
            )
            self.assertEqual(rejeitar.status_code, 302)
            rg.refresh_from_db()
            self.assertEqual(rg.status_aprovacao, StatusAprovacaoDocumento.REJEITADO)
            self.assertEqual(rg.motivo_rejeicao, "Documento ilegível.")
            licenca.refresh_from_db()
            self.assertEqual(licenca.status, StatusLicenca.PENDENCIA_DOCUMENTAL)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_ambulante_ve_pendencia_e_reenvia(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            override_settings(MEDIA_ROOT=tmp),
        ):
            rg = self._criar_documento(TipoDocumento.RG_CPF, "rg.pdf")
            rg.rejeitar("Frente do RG cortada.")
            licenca, _criado = abrir_requerimento(
                self.ambulante, categoria=self.categoria
            )
            licenca.status = StatusLicenca.PENDENCIA_DOCUMENTAL
            licenca.save(update_fields=["status"])

            self.client.force_login(self.ambulante)
            pagina = self.client.get(reverse("ambulante_cadastro"), {"etapa": 6})
            self.assertContains(pagina, "Frente do RG cortada.")
            self.assertContains(pagina, "Rejeitado")
            self.assertContains(pagina, "Pendência documental")

            painel = self.client.get(reverse("ambulante_painel"))
            self.assertContains(painel, "há pendência documental")
            self.assertContains(painel, "Reenviar documentos")

            reenvio = self.client.post(
                reverse("ambulante_cadastro"),
                {
                    "etapa": "6",
                    "acao": "salvar",
                    "arquivo_rg_cpf": _pdf("rg-novo.pdf"),
                },
            )
            self.assertEqual(reenvio.status_code, 302)
            rg.refresh_from_db()
            self.assertEqual(rg.status_aprovacao, StatusAprovacaoDocumento.PENDENTE)
            self.assertEqual(rg.motivo_rejeicao, "")
            licenca.refresh_from_db()
            self.assertEqual(licenca.status, StatusLicenca.EM_ANALISE)

    @pytest.mark.skip(reason="Funcionalidade mockada/legada do hackathon")
    def test_laudo_obrigatorio_bloqueia_avanco(self):
        self.assertFalse(pode_avancar_solicitacao(self.ambulante, self.categoria))
        self.assertIn(
            TipoDocumento.LAUDO_SANITARIO,
            tipos_faltando_aprovacao(self.ambulante, self.categoria),
        )
        self.assertIn(
            TipoDocumento.LAUDO_BOMBEIROS,
            tipos_faltando_aprovacao(self.ambulante, self.categoria),
        )

        with (
            tempfile.TemporaryDirectory() as tmp,
            override_settings(MEDIA_ROOT=tmp),
        ):
            for tipo, nome in (
                (TipoDocumento.COMPROVANTE_RESIDENCIA, "comp.pdf"),
                (TipoDocumento.RG_CPF, "rg.pdf"),
                (TipoDocumento.LAUDO_SANITARIO, "sanitario.pdf"),
                (TipoDocumento.LAUDO_BOMBEIROS, "bombeiros.pdf"),
            ):
                doc = self._criar_documento(tipo, nome)
                doc.aprovar()

        self.assertTrue(pode_avancar_solicitacao(self.ambulante, self.categoria))

        licenca, _criado = abrir_requerimento(self.ambulante, categoria=self.categoria)
        DocumentoAnexo.objects.filter(
            tipo_documento=TipoDocumento.LAUDO_SANITARIO
        ).update(status_aprovacao=StatusAprovacaoDocumento.PENDENTE)

        with self.assertRaises(ValidationError):
            aplicar_parecer(licenca, self.gestor, "deferir")
