from django import forms
from django.contrib.auth import get_user_model

from .models import (AppointmentRequest, CalendarSettings, DayOff, Service,
                     StaffMember, WorkingHours)
from .utils.validators import not_in_the_past


class AppointmentRequestForm(forms.ModelForm):
    class Meta:
        model = AppointmentRequest
        fields = ("date", "start_time", "end_time", "service", "staff_member")


class SlotForm(forms.Form):
    selected_date = forms.DateField(validators=[not_in_the_past])
    service = forms.ModelChoiceField(
        Service.objects.all(),
        error_messages={"invalid_choice": "Service does not exist"},
    )
    staff_member = forms.ModelChoiceField(
        StaffMember.objects.all(),
        error_messages={"invalid_choice": "Мастер не выбран"},
    )


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "description", "duration", "price", "image"]
        labels = {
            "name": "Название",
            "description": "Описание",
            "duration": "Продолжительность",
            "price": "Цена",
            "image": "Фотография",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "label": "Название",
                    "class": "form-control",
                    "placeholder": "Пример: Наращивание",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "label": "Название",
                    "class": "form-control",
                    "placeholder": "Пример: Описание для клиентов.",
                }
            ),
            "duration": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "ЧЧ:MM:СС, (Пример: 00:15:00 для 15 минут)",
                }
            ),
            "price": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Пример: 100.00"}
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class ClientDataForm(forms.Form):
    name = forms.CharField(
        max_length=50, widget=forms.TextInput(attrs={"class": "form-control"})
    )
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))


class StaffMemberForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = [
            "user",
            "services_offered",
            "slot_duration",
            "lead_time",
            "finish_time",
            "appointment_buffer_time",
        ]
        labels = {
            "user": "Выберите пользователя:",
            "services_offered": "Выберите услуги для работника:",
            "slot_duration": "Частота записи в минутах:",
            "lead_time": "Время начала работы:",
            "finish_time": "Время окончания работы:",
            "appointment_buffer_time": "Через сколько будет разрешена"
                                       " запись с начала рабочего времени:",
        }
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "service_offered": forms.Select(attrs={"class": "form-control"}),
            "slot_duration": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "15, 30, 60... (в минутах). Pекомендуемое 30",
                }
            ),
            "lead_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Пример значений: 08:00:00, "
                                   "09:00:00... (24-часовой формат)",
                }
            ),
            "finish_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Пример значений: 17:00:00, "
                                   "18:00:00... (24-часовой формат)",
                }
            ),
            "appointment_buffer_time": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Пример значений: 15, 30, 45, 60... (в минутах)",
                }
            ),
        }


class PersonalInformationForm(forms.Form):
    # first_name, last_name, email
    first_name = forms.CharField(
        max_length=50,
        label="Имя:",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=50,
        label="Фамилия",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Email", widget=forms.EmailInput(attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # pop the user from the kwargs
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if self.user:
            if self.user.email == email:
                return email
            queryset = get_user_model().objects.exclude(pk=self.user.pk)
        else:
            queryset = get_user_model().objects.all()

        if queryset.filter(email=email).exists():
            raise forms.ValidationError("This email is already taken.")
        return email


class StaffAppointmentInformationForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = [
            "services_offered",
            "slot_duration",
            "lead_time",
            "finish_time",
            "appointment_buffer_time",
        ]
        labels = {
            "services_offered": "Выберите услуги для работника:",
            "slot_duration": "Частота записи в минутах:",
            "lead_time": "Время начала работы:",
            "finish_time": "Время окончания работы:",
            "appointment_buffer_time": "Через сколько будет разрешена запись"
                                       " с начала рабочего времени:",
        }
        widgets = {
            "service_offered": forms.Select(attrs={"class": "form-control"}),
            "slot_duration": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Пример значений: 30, 60, 90, 120... (в минутах)",
                }
            ),
            "lead_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Пример значений: 08:00:00, 09:00:00... (24-часовой формат)",
                }
            ),
            "finish_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Пример значений: 17:00:00, 18:00:00... (24-часовой формат)",
                }
            ),
            "appointment_buffer_time": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Пример значений: 15, 30, 45, 60... (в минутах)",
                }
            ),
        }


class StaffDaysOffForm(forms.ModelForm):
    class Meta:
        model = DayOff
        fields = ["start_date", "end_date", "description"]
        widgets = {
            "start_date": forms.DateInput(
                attrs={
                    "class": "datepicker",
                }
            ),
            "end_date": forms.DateInput(
                attrs={
                    "class": "datepicker",
                }
            ),
            "duration": forms.TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class StaffWorkingHoursForm(forms.ModelForm):
    class Meta:
        model = WorkingHours
        fields = ["day_of_week", "start_time", "end_time"]


class CalendarSettingsForm(forms.ModelForm):
    class Meta:
        model = CalendarSettings
        fields = ["duration"]
        widgets = {
            "duration": forms.Select(attrs={"class": "form-control"}),
        }
