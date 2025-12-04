from django.db import models
from datetime import date

OPCOES_SERVICOS = [
    ('DEGRADE', 'Degradê'), ('SOCIAL', 'Social'), ('PEZIM', 'Pezim'),
    ('BARBA', 'Barba'), ('SOBRANCELHA', 'Sobrancelha'), ('LUZES', 'Luzes'),
    ('PLATINADO', 'Platinado'), ('ALISAMENTO', 'Alisamento'),
    ('PIGMENTACAO', 'Pigmentação'), ('COMPLETO', 'Combo Completo'), ('OUTRO', 'Outro')
]

OPCOES_BARBEIROS = [('LUCAS', 'Lucas Borges'), ('ALUIZIO', 'Aluízio'), ('ERIK', 'Erik')]
OPCOES_VENDEDORES = OPCOES_BARBEIROS + [('FABRICIO', 'Fabrício')]
OPCOES_PAGAMENTO = [('DINHEIRO', 'Dinheiro'), ('PIX', 'Pix'), ('CARTAO', 'Cartão'), ('MISTO', 'Misto')]

class Agendamento(models.Model):
    data = models.DateField(default=date.today)
    horario = models.TimeField()
    cliente = models.CharField(max_length=100)
    barbeiro = models.CharField(max_length=20, choices=OPCOES_BARBEIROS)
    servico = models.CharField(max_length=20, choices=OPCOES_SERVICOS)
    com_barba = models.BooleanField(default=False)
    forma_pagamento = models.CharField(max_length=20, choices=OPCOES_PAGAMENTO)
    valor_total = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Misto
    valor_1 = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    tipo_pagamento_1 = models.CharField(max_length=20, blank=True, null=True)
    valor_2 = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    tipo_pagamento_2 = models.CharField(max_length=20, blank=True, null=True)

    criado_em = models.DateTimeField(auto_now_add=True)

class Venda(models.Model):
    data = models.DateField(default=date.today)
    item = models.CharField(max_length=200, verbose_name="Descrição do Produto")
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    vendedor = models.CharField(max_length=50, choices=OPCOES_VENDEDORES)

class Saida(models.Model):
    data = models.DateField(default=date.today)
    descricao = models.CharField(max_length=200, verbose_name="Descrição da Saída")
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    # Categoria removida conforme solicitado