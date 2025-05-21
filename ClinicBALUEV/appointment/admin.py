from django.contrib import admin

from .forms import StaffMemberForm
from .models import Config, Service, StaffMember, WorkingHours, Appointment, Specialization


# Register your models here.


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "duration", "price", "created_at")
    search_fields = ("name",)
    list_filter = ("duration",)

@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    pass
@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = (
        "slot_duration",
        "lead_time",
        "finish_time",
        "appointment_buffer_time",
    )

@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    form = StaffMemberForm
    list_display = (
        "get_staff_member_name",
        "get_slot_duration",
        "lead_time",
        "finish_time",
    )
    search_fields = ("user__email", "user__first_name", "user__last_name")


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ("staff_member", "day_of_week", "start_time", "end_time")
    search_fields = ("day_of_week",)
    list_filter = ("day_of_week", "start_time", "end_time")

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    pass