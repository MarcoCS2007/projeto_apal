import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.usuarios.models import ConfiguracaoSeguranca
from apps.usuarios.tests import UsuariosAuthFixtures


class CpfMascaradoTests(UsuariosAuthFixtures, TestCase):
    def test_lista_de_ambulantes_mascara_cpf(self):
        self.client.force_login(self.gestor)
        response = self.client.get(reverse("gestor_ambulantes"))
        self.assertContains(response, self.ambulante.cpf_mascarado)
        self.assertNotContains(response, self.ambulante.cpf_formatado)


class BackupBancoTests(UsuariosAuthFixtures, TestCase):
    def test_master_gera_backup_restauravel(self):
        with tempfile.TemporaryDirectory() as pasta, override_settings(
            BACKUP_ROOT=Path(pasta)
        ):
            self.client.force_login(self.administrador)
            response = self.client.post(reverse("master_backup"))
            self.assertEqual(response.status_code, 302)
            arquivos = list(Path(pasta).glob("apal_backup_*.json"))
            self.assertEqual(len(arquivos), 1)
            self.assertGreater(arquivos[0].stat().st_size, 0)

            painel = self.client.get(reverse("master_admin"))
            self.assertContains(painel, arquivos[0].name)

    def test_comando_backup_banco(self):
        with tempfile.TemporaryDirectory() as pasta, override_settings(
            BACKUP_ROOT=Path(pasta)
        ):
            call_command("backup_banco")
            self.assertTrue(any(Path(pasta).glob("apal_backup_*.json")))


class PrivacidadeTests(TestCase):
    def test_pagina_publica_cita_base_legal_e_retencao(self):
        ConfiguracaoSeguranca.carregar()
        response = self.client.get(reverse("privacidade"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LGPD")
        self.assertContains(response, "12")
