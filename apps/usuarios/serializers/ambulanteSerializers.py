from rest_framework import serializers
import uuid
from ..models import Ambulante
from django.db import transaction


class RegisterAmbulante(serializers.ModelSerializer):
    # Campos herdados de UsuarioBase declarados explicitamente
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Ambulante
        fields = '__all__'
        read_only_fields = ('codigo_qr_code', 'pontuacao')
        

    def create(self, validated_data):
        password = validated_data.pop("password")

        # Gera um token único de QR Code para o cadastro inicial
        codigo_qr_code = str(uuid.uuid4())

        # (Critério 2) Criação do UsuarioBase e Ambulante na mesma transação no banco
        with transaction.atomic():
            ambulante = Ambulante(codigo_qr_code=codigo_qr_code, **validated_data)
            # Criptografa a senha no UsuarioBase herdado
            ambulante.set_password(password)
            ambulante.save()

            return ambulante
    