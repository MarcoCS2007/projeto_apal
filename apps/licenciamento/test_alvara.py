from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.espacos.models import (
    Endereco,
    EstruturaTrabalho,
    PontoOcupacao,
    StatusOcupacao,
)
from apps.licenciamento.models import CategoriaProduto, LicencaAlvara, StatusLicenca
from apps.licenciamento.services import abrir_requerimento, renovar_licenca
from apps.usuarios.models import Ambulante
from apps.usuarios.tests import UsuariosAuthFixtures


class AlvaraAmbulanteTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.categoria = CategoriaProduto.objects.create(
            nome_categoria="Alimentos Manipulados",
            descricao="Alimentos preparados na hora.",
        )
        self.ponto = PontoOcupacao.objects.create(
            nome_identificacao="Praça Central",
            logradouro="Praça Barão do Rio Branco",
            bairro="Centro",
            metragem_maxima=Decimal("10.00"),
            status_ocupacao=StatusOcupacao.LIVRE,
        )
        self._completar(self.ambulante)
        self.url = reverse("ambulante_alvara")

    def _completar(self, ambulante):
        ambulante.tipo_atuacao = "fixo"
        ambulante.ponto_pretendido = self.ponto
        extras = dict(ambulante.dados_complementares or {})
        extras["categoria_id"] = self.categoria.pk
        extras["categoria_nome"] = self.categoria.nome_categoria
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

    def test_anonimo_e_redirecionado_ao_entrar(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("entrar"), response.url)

    def test_gestor_nao_acessa_alvara_do_ambulante(self):
        self.client.force_login(self.gestor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backoffice_inicio"))

    def test_sem_solicitacao_mostra_estado_vazio(self):
        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma solicitação ainda")

    def test_protocolo_visivel_com_ponto_categoria_e_status(self):
        licenca, _criado = abrir_requerimento(self.ambulante, self.categoria)
        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, licenca.protocolo)
        self.assertContains(response, "Em Análise")
        self.assertContains(response, "Praça Central")
        self.assertContains(response, "Alimentos Manipulados")
        self.assertContains(response, "João Ambulante")
        self.assertContains(response, "Histórico de requerimentos")

        painel = self.client.get(reverse("ambulante_painel"))
        self.assertContains(painel, licenca.protocolo)
        self.assertContains(painel, reverse("ambulante_alvara"))

        self.client.logout()
        self.client.force_login(self.gestor)
        fila = self.client.get(reverse("gestor_fila"))
        self.assertContains(fila, licenca.protocolo)

    def test_indeferimento_mostra_motivo(self):
        licenca, _criado = abrir_requerimento(self.ambulante, self.categoria)
        licenca.status = StatusLicenca.INDEFERIDO
        licenca.motivo_parecer = "Ponto incompatível com a estrutura."
        licenca.save()

        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)
        self.assertContains(response, "Indeferido")
        self.assertContains(response, "Ponto incompatível com a estrutura.")

    def test_pendencia_oferece_reenvio_de_documentos(self):
        licenca, _criado = abrir_requerimento(self.ambulante, self.categoria)
        licenca.status = StatusLicenca.PENDENCIA_DOCUMENTAL
        licenca.save(update_fields=["status"])

        self.client.force_login(self.ambulante)
        response = self.client.get(self.url)
        self.assertContains(response, "Pendência Documental")
        self.assertContains(response, reverse("ambulante_cadastro"))
        self.assertContains(response, "Reenviar documentos")

    def test_aprovado_permite_simular_pagamento_htmx(self):
        licenca, _criado = abrir_requerimento(self.ambulante, self.categoria)
        licenca.status = StatusLicenca.APROVADO
        licenca.save(update_fields=["status"])

        self.client.force_login(self.ambulante)
        pagina = self.client.get(self.url)
        self.assertContains(pagina, "Aguardando Pagamento da Taxa")
        self.assertContains(pagina, "Simular pagamento da taxa")
        self.assertContains(pagina, "R$ 120")

        pagamento = self.client.post(
            reverse("alvara_simular_pagamento", args=[licenca.pk]),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(pagamento.status_code, 200)
        self.assertContains(pagamento, "Pagamento da taxa confirmado")
        licenca.refresh_from_db()
        self.assertTrue(licenca.taxa_paga)
        self.assertEqual(licenca.status, StatusLicenca.APROVADO)
        self.assertIsNone(licenca.numero_licenca)

    def test_nao_paga_taxa_de_outro_ambulante(self):
        outro = Ambulante.objects.create_user(
            cpf="88899900011",
            email="outro.alvara@email.com",
            password=self.senha,
            nome="Outro",
            sobrenome="Ambulante",
            telefone_whatsapp="77911111111",
        )
        licenca = LicencaAlvara.objects.create(
            ambulante=outro,
            ponto_ocupacao=self.ponto,
            categoria_produto=self.categoria,
            status=StatusLicenca.APROVADO,
        )

        self.client.force_login(self.ambulante)
        response = self.client.post(
            reverse("alvara_simular_pagamento", args=[licenca.pk])
        )
        self.assertEqual(response.status_code, 404)
        licenca.refresh_from_db()
        self.assertFalse(licenca.taxa_paga)

    def test_renovar_licenca_vencida_abre_novo_protocolo(self):
        licenca, _criado = abrir_requerimento(self.ambulante, self.categoria)
        licenca.status = StatusLicenca.VENCIDO
        licenca.save(update_fields=["status"])

        self.client.force_login(self.ambulante)
        pagina = self.client.get(self.url)
        self.assertContains(pagina, "Renovar licença")

        response = self.client.post(reverse("ambulante_renovar", args=[licenca.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)

        nova = LicencaAlvara.objects.exclude(pk=licenca.pk).get(
            ambulante=self.ambulante
        )
        self.assertEqual(nova.status, StatusLicenca.EM_ANALISE)
        self.assertEqual(nova.licenca_origem_id, licenca.pk)
        self.assertEqual(nova.tipo_pedido, "Renovação")

        alvara = self.client.get(self.url)
        self.assertContains(alvara, nova.protocolo)
        self.assertContains(alvara, "Renovação")

        self.client.logout()
        self.client.force_login(self.gestor)
        fila = self.client.get(reverse("gestor_fila"))
        self.assertContains(fila, nova.protocolo)

    def test_renovar_nao_duplica_requerimento_em_aberto(self):
        vencida, _criado = abrir_requerimento(self.ambulante, self.categoria)
        vencida.status = StatusLicenca.VENCIDO
        vencida.save(update_fields=["status"])
        nova, criada = renovar_licenca(vencida, self.ambulante)
        self.assertTrue(criada)

        de_novo, criada_de_novo = renovar_licenca(vencida, self.ambulante)
        self.assertFalse(criada_de_novo)
        self.assertEqual(de_novo.pk, nova.pk)
        self.assertEqual(
            LicencaAlvara.objects.filter(ambulante=self.ambulante).count(), 2
        )
