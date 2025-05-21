import datetime
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

from .utils.date_time import (convert_minutes_in_human_readable_format,
                              get_timestamp)
from .utils.view_helpers import generate_random_id

# Create your models here.

DAYS_OF_WEEK = (
    (0, "Воскресенье"),
    (1, "Понедельник"),
    (2, "Вторник"),
    (3, "Среда"),
    (4, "Четверг"),
    (5, "Пятница"),
    (6, "Суббота"),
)


class Service(models.Model):
    name = models.CharField(max_length=100, blank=False)
    description = models.TextField(blank=True, null=True)
    duration = models.DurationField(
        validators=[MinValueValidator(datetime.timedelta(seconds=1))]
    )
    price = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    image = models.ImageField(upload_to="services/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_duration_parts(self):
        total_seconds = int(self.duration.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return days, hours, minutes, seconds

    def get_duration(self):
        days, hours, minutes, seconds = self.get_duration_parts()
        parts = []

        if days:
            parts.append(f"{days} day{'s' if days > 1 else ''}")
        if hours:
            parts.append(f"{hours} час{'а' if hours > 1 else ''}")
        if minutes:
            parts.append(f"{minutes} минут")
        if seconds:
            parts.append(f"{seconds} секунд{'ы' if seconds > 1 else ''}")

        return " ".join(parts)

    def get_price(self):
        # Check if the decimal part is 0
        return f"{self.price} рублей"

    def get_image_url(self):
        if not self.image:
            return ""
        return self.image.url

    def get_description(self):
        return self.description

class Specialization(models.Model):
    name = models.CharField("Название специализации", max_length=100)
    description = models.TextField("Описание", blank=True)

    class Meta:
        verbose_name = "Специализация"
        verbose_name_plural = "Специализации"

    def __str__(self):
        return self.name


class StaffMember(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    services_offered = models.ManyToManyField(Service)
    slot_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="(Количество слотов доступных для записи к данному работнику, день будет разбит на промежутки по"
                  " установленному количеству минут)",
    )
    lead_time = models.TimeField(
        null=True, blank=True, help_text="Время начала рабочего дня"
    )
    finish_time = models.TimeField(
        null=True, blank=True, help_text="Время конца рабочего дня"
    )
    appointment_buffer_time = models.FloatField(
        blank=True,
        null=True,
        help_text="Время между текущим моментом и первым доступным интервалом на текущий день (не влияет на завтра)",
    )
    image = models.ImageField(upload_to="staffmembers/", blank=True, null=True)
    specializations = models.ManyToManyField(
        Specialization,
        blank=True,
        verbose_name="Специализации"
    )

    def __str__(self):
        return f"{self.get_staff_member_name()}"

    def get_image_url(self):
        if not self.image:
            return ""
        return self.image.url

    def get_lead_time(self):
        config = Config.objects.first()
        return self.lead_time or (config.lead_time if config else None)

    def get_staff_member_name(self):
        name_options = [
            getattr(self.user, "get_full_name", lambda: "")(),
            f"{self.user.first_name} {self.user.last_name}",
            self.user.username,
            self.user.email,
            f"Staff Member {self.id}",
        ]
        return next((name.strip() for name in name_options if name.strip()), "Unknown")

    def get_staff_member_first_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def get_days_off(self):
        return DayOff.objects.filter(staff_member=self)

    def get_finish_time(self):
        config = Config.objects.first()
        return self.finish_time or (config.finish_time if config else None)

    def get_slot_duration(self):
        config = Config.objects.first()
        return self.slot_duration or (config.slot_duration if config else 0)

    def get_working_hours(self):
        return self.workinghours_set.all()

    def get_services_offered(self):
        return self.services_offered.all()

    def get_slot_duration_text(self):
        slot_duration = self.get_slot_duration()
        return convert_minutes_in_human_readable_format(slot_duration)

    def get_appointment_buffer_time(self):
        config = Config.objects.first()
        return self.appointment_buffer_time or (
            config.appointment_buffer_time if config else 0
        )

    def get_service_is_offered(self, service_id):
        return self.services_offered.filter(id=service_id).exists()

    def get_appointment_buffer_time_text(self):
        # convert buffer time (which is in minutes) in day hours minutes if necessary
        return convert_minutes_in_human_readable_format(
            self.get_appointment_buffer_time()
        )

class AppointmentRequest(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    staff_member = models.ForeignKey(StaffMember, on_delete=models.SET_NULL, null=True)
    id_request = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.date} - {self.start_time} to {self.end_time} - {self.service.name}"
        )

    def clean(self):
        if self.start_time is not None and self.end_time is not None:
            if self.start_time > self.end_time:
                raise ValidationError("Start time must be before end time")
            if self.start_time == self.end_time:
                raise ValidationError("Start time and end time cannot be the same")

        # Ensure the date is not in the past:
        if self.date and self.date < datetime.date.today():
            raise ValidationError("Date cannot be in the past")

    def save(self, *args, **kwargs):
        # if no id_request is provided, generate one
        if self.id_request is None:
            self.id_request = (
                f"{get_timestamp()}{self.service.id}{generate_random_id()}"
            )
        # start time should not be equal to end time
        if self.start_time == self.end_time:
            raise ValidationError("Start time and end time cannot be the same")
        # date should not be in the past
        # duration should not exceed the service duration
        return super().save(*args, **kwargs)

    def get_service_name(self):
        return self.service.name

    def get_ar_date(self):
        return self.date

    def get_start_time(self):
        return datetime.datetime.combine(
            self.date, self.start_time
        )

    def get_end_time(self):
        return datetime.datetime.combine(
            self.date, self.end_time
        )

    def get_service_duration(self):
        return self.service.get_duration()

    def get_service_price(self):
        return self.service.get_price()

    def get_service_down_payment(self):
        return self.service.get_down_payment()

    def get_service_image(self):
        return self.service.image

    def get_service_image_url(self):
        return self.service.get_image_url()

    def get_service_description(self):
        return self.service.description

    def get_id_request(self):
        return self.id_request


class ArchivedAppointmentRequest(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    staff_member = models.ForeignKey(StaffMember, on_delete=models.SET_NULL, null=True)
    id_request = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.date} - {self.start_time} to {self.end_time} - {self.service.name}"
        )

    def get_service_name(self):
        return self.service.name

    def get_service_price(self):
        return self.service.get_price()

    def get_service_image(self):
        return self.service.image

    def get_service_image_url(self):
        return self.service.get_image_url()

    def get_service_description(self):
        return self.service.description

    def get_id_request(self):
        return self.id_request


class Appointment(models.Model):
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    appointment_request = models.OneToOneField(
        AppointmentRequest, on_delete=models.CASCADE
    )
    id_request = models.CharField(max_length=100, blank=True, null=True)
    not_come = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.client} - "
            f"{self.appointment_request.start_time.strftime('%Y-%m-%d %H:%M')} to "
            f"{self.appointment_request.end_time.strftime('%Y-%m-%d %H:%M')}"
        )

    def save(self, *args, **kwargs):
        if not hasattr(self, "appointment_request"):
            raise ValidationError("Appointment request is required")
        return super().save(*args, **kwargs)

    def get_client_name(self):
        if hasattr(self.client, "get_full_name") and callable(
                getattr(self.client, "get_full_name")
        ):
            name = self.client.get_full_name()
        else:
            name = self.client.first_name
        return name

    def get_date(self):
        return self.appointment_request.date

    def get_start_time(self):
        return datetime.datetime.combine(
            self.get_date(), self.appointment_request.start_time
        )

    def get_end_time(self):
        return datetime.datetime.combine(
            self.get_date(), self.appointment_request.end_time
        )

    def get_service(self):
        return self.appointment_request.service

    def get_service_name(self):
        return self.appointment_request.get_service_name()

    def get_service_duration(self):
        return self.appointment_request.service.get_duration()

    def get_staff_member_name(self):
        if not self.appointment_request.staff_member:
            return ""
        return self.appointment_request.staff_member.get_staff_member_name()

    def get_staff_member(self):
        return self.appointment_request.staff_member

    def get_service_price(self):
        return self.appointment_request.get_service_price()

    def get_service_down_payment(self):
        return self.appointment_request.get_service_down_payment()

    def get_service_img(self):
        return self.appointment_request.get_service_image()

    def get_service_img_url(self):
        return self.appointment_request.get_service_image_url()

    def get_service_description(self):
        return self.appointment_request.get_service_description()

    def get_appointment_date(self):
        return self.appointment_request.date

    def get_appointment_id_request(self):
        return self.id_request

    def get_absolute_url(self, request=None):
        url = reverse('display_appointment', args=[str(self.id)])
        return request.build_absolute_uri(url) if request else url

    def is_owner(self, staff_user_id):
        return self.appointment_request.staff_member.user.id == staff_user_id


class ArchivedAppointment(models.Model):
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    appointment_request = models.OneToOneField(
        ArchivedAppointmentRequest, on_delete=models.CASCADE
    )
    id_request = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.client} - "
            f"{self.appointment_request.start_time.strftime('%Y-%m-%d %H:%M')} to "
            f"{self.appointment_request.end_time.strftime('%Y-%m-%d %H:%M')}"
        )

    def get_client_name(self):
        if hasattr(self.client, "get_full_name") and callable(
                getattr(self.client, "get_full_name")
        ):
            name = self.client.get_full_name()
        else:
            name = self.client.first_name
        return name

    def get_date(self):
        return self.appointment_request.date

    def get_start_time(self):
        return datetime.datetime.combine(
            self.get_date(), self.appointment_request.start_time
        )

    def get_end_time(self):
        return datetime.datetime.combine(
            self.get_date(), self.appointment_request.end_time
        )

    def get_service(self):
        return self.appointment_request.service

    def get_service_name(self):
        return self.appointment_request.get_service_name()

    def get_service_duration(self):
        return self.appointment_request.service.get_duration()

    def get_staff_member_name(self):
        if not self.appointment_request.staff_member:
            return ""
        return self.appointment_request.staff_member.get_staff_member_name()

    def get_staff_member(self):
        return self.appointment_request.staff_member

    def get_service_price(self):
        return self.appointment_request.get_service_price()

    def get_service_down_payment(self):
        return self.appointment_request.get_service_down_payment()

    def get_service_img(self):
        return self.appointment_request.get_service_image()

    def get_service_img_url(self):
        return self.appointment_request.get_service_image_url()

    def get_service_description(self):
        return self.appointment_request.get_service_description()

    def get_appointment_date(self):
        return self.appointment_request.date

    def get_appointment_id_request(self):
        return self.id_request

    def get_absolute_url(self, request=None):
        url = reverse('display_appointment', args=[str(self.id)])
        return request.build_absolute_uri(url) if request else url

    def is_owner(self, staff_user_id):
        return self.appointment_request.staff_member.user.id == staff_user_id


class Config(models.Model):
    slot_duration = models.PositiveIntegerField(
        null=True,
        help_text="Minimum time for an appointment in minutes, recommended 30.",
    )

    lead_time = models.TimeField(null=True, help_text="Time when we start working.")
    finish_time = models.TimeField(null=True, help_text="Time when we stop working.")
    appointment_buffer_time = models.FloatField(
        null=True,
        help_text="Time between now and the first available slot for the current day (doesn't affect tomorrow).",
    )


class WorkingHours(models.Model):
    staff_member = models.ForeignKey(StaffMember, on_delete=models.CASCADE)
    day_of_week = models.PositiveIntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return (
            f"{self.get_day_of_week_display()} - {self.start_time} to {self.end_time}"
        )

    def get_day_of_week_str(self):
        # return the name of the day instead of the integer
        return self.get_day_of_week_display()

    def is_owner(self, user_id):
        return self.staff_member.user.id == user_id


class DayOff(models.Model):
    staff_member = models.ForeignKey(StaffMember, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.CharField(max_length=255, blank=True, null=True)

    # meta data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.start_date} to {self.end_date} - {self.description if self.description else 'Day off'}"

    def clean(self):
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValidationError("Start date must be before end date")

    def is_owner(self, user_id):
        return self.staff_member.user.id == user_id


class CalendarSettings(models.Model):
    DURATION_CHOICES = [
        (7, "1 неделя"),
        (14, "2 недели"),
        (21, "3 недели"),
        (30, "1 месяц"),
        (45, "1.5 месяца"),
        (60, "2 месяца"),
    ]
    staff_member = models.OneToOneField(StaffMember, on_delete=models.CASCADE)
    duration = models.IntegerField(choices=DURATION_CHOICES, default=30)

    def get_end_date(self):
        """Вычисляет конечную дату на основе выбранной длительности"""
        return date.today() + timedelta(days=self.duration)

    def __str__(self):
        return f"Календарь: {date.today()} - {self.get_end_date()}"
