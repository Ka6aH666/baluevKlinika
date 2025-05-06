from django import forms


class UserRegisterForm(forms.Form):
    username = forms.CharField(
        label="Логин",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ваш логин"}
        )
    )
    first_name = forms.CharField(
        label="Имя",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Имя"}
        )
    )
    last_name = forms.CharField(
        label="Фамилия",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Фамилия"}
        )
    )
    email = forms.EmailField(
        label="Электронная почта",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Электронная почта"}
        )
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Введите пароль"}
        )
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Повторите пароль"}
        )
    )
    social_link_tg = forms.CharField(
        label="Telegram",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ссылка на Telegram"}
        )
    )
    social_link_vk = forms.CharField(
        label="VK",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Ссылка на VK"}
        )
    )
    phone_number = forms.CharField(
        label="Номер телефона",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Номер телефона"}
        )
    )

    def clean(self):
        cleaned_data = super().clean()
        social_link_tg = cleaned_data.get("social_link_tg")
        social_link_vk = cleaned_data.get("social_link_vk")
        pswd = cleaned_data.get("password")
        pswd2 = cleaned_data.get("password2")

        if not social_link_tg and not social_link_vk:
            self.add_error('social_link_vk', 'Укажите верно хотя бы одно: Telegram или VK.')
            self.add_error('social_link_tg', 'Укажите верно хотя бы одно: Telegram или VK.')
        if pswd2 != pswd:
            self.add_error('password2', 'Введенный пароль не совпадает')
        return cleaned_data
