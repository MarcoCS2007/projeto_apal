from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.assistente.models import LogAssistente
from apps.core.ia import consultar_conhecimento
from apps.usuarios.tests import UsuariosAuthFixtures


class ConsultaConhecimentoTests(SimpleTestCase):
    def test_documentos_para_alimentos_cita_laudo_sanitario(self):
        resultado = consultar_conhecimento("quais documentos preciso para alimentos?")
        texto = resultado.texto.lower()
        self.assertEqual(resultado.trecho_id, "documentos_alimentos")
        self.assertIn("vigilância sanitária", texto)
        self.assertIn("laudo", texto)

    def test_prazos_de_renovacao(self):
        resultado = consultar_conhecimento("quais os prazos de renovação?")
        self.assertEqual(resultado.trecho_id, "prazos")
        self.assertIn("31 de dezembro", resultado.texto)

    def test_pergunta_vazia_usa_fallback(self):
        resultado = consultar_conhecimento("???")
        self.assertEqual(resultado.trecho_id, "fallback")


class AssistenteAmbulanteTests(UsuariosAuthFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("ambulante_assistente")

    def test_anonimo_vai_ao_entrar(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("entrar"), response.url)

    def test_pergunta_grava_log_e_aparece_no_master(self):
        pergunta = "quais documentos preciso para alimentos?"
        self.client.force_login(self.ambulante)
        response = self.client.post(self.url, {"pergunta": pergunta})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)

        log = LogAssistente.objects.get()
        self.assertEqual(log.ambulante, self.ambulante)
        self.assertEqual(log.pergunta, pergunta)
        self.assertIn("Vigilância Sanitária", log.resposta)
        self.assertIn("laudo", log.resposta.lower())

        pagina = self.client.get(self.url)
        self.assertContains(pagina, pergunta)
        self.assertContains(pagina, "Vigilância Sanitária")

        self.client.force_login(self.administrador)
        auditoria = self.client.get(reverse("master_logs_ia"))
        self.assertContains(auditoria, pergunta)
        self.assertContains(auditoria, "laudo sanit")
        self.assertEqual(auditoria.context["total_logs"], 1)
