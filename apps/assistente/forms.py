from django import forms


class PerguntaAssistenteForm(forms.Form):
    pergunta = forms.CharField(
        label="Sua pergunta",
        max_length=500,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Ex.: quais documentos preciso para alimentos?",
                "maxlength": "500",
            }
        ),
    )

    def clean_pergunta(self):
        texto = self.cleaned_data["pergunta"].strip()
        if not texto:
            raise forms.ValidationError("Digite uma pergunta.")
        return texto
