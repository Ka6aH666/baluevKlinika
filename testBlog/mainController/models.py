from django.db import models

# Create your models here.
# привет

class Meet(models.Model):
    """Модель записи."""

    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    date = models.DateField()
    time_slot = models.ForeignKey("Chank", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} {self.surname} - {self.date} - {self.time_slot}"

    class Meta:
        verbose_name = "Записи"
        verbose_name_plural = "Записи"


class Chank(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.start_time} - {self.end_time}"
