from datetime import time

from testBlog.appointment.models import Config

lead_time = time(9, 0)
finish_time = time(17, 0)
slot_duration = 30
appointment_buffer_time = 0

Config.objects.create(
    lead_time=lead_time,
    finish_time=finish_time,
    slot_duration=slot_duration,
    appointment_buffer_time=appointment_buffer_time,
)
