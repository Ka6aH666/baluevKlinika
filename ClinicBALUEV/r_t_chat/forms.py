from django import forms
from django.forms import ModelForm

from .models import GroupMessage


class ChatmessageCreateForm(ModelForm):
    class Meta:
        model = GroupMessage
        fields = ["body"]
        labels = {"body": ""}
        widgets = {
            "body": forms.TextInput(attrs={'placeholder': 'Введите сообщение...', 'class': 'form-control', 'maxlength': '300', 'autofocus': True }),
        }
