from django import forms


class TelegramIDForm(forms.Form):
    tg_id = forms.CharField(max_length=20)


class VerificationCodeForm(forms.Form):
    code = forms.CharField(max_length=8)
