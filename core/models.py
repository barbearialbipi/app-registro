from django.db import models

class Agendamento(models.Model):
    cliente = models.CharField(max_length=100)
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.cliente
