from django.db import models
from datetime import date

# --- OPÇÕES (Menus Dropdown) ---
OPCOES_BARBEIROS = [
    ('LUCAS', 'Lucas Borges'),
    ('ALUIZIO', 'Aluízio'),
    ('ERIK', 'Erik'),
]

OPCOES_SERVICOS = [
    ('DEGRADE', 'Degradê'),
    ('PEZIM', 'Pezim'),
    ('BARBA', 'Barba'),
    ('SOCIAL', 'Social'),
    ('COMPLETO', 'Combo Completo'),
    ('OUTRO', 'Outro'),
]

OPCOES_PAGAMENTO = [
    ('DINHEIRO', 'Dinheiro'),
    ('PIX', 'Pix'),
    ('CARTAO', 'Cartão'),
    ('MISTO', 'Misto (Dinheiro/Pix/Cartão)'),
]

# --- TABELAS ---

class Agendamento(models.Model):
    data = models.DateField(default=date.today, verbose_name="Data do Corte")
    horario = models.TimeField(verbose_name="Horário", null=True, blank=True) # Opcional
    cliente = models.CharField(max_length=100)
    
    barbeiro = models.CharField(max_length=20, choices=OPCOES_BARBEIROS)
    servico = models.CharField(max_length=20, choices=OPCOES_SERVICOS)
    
    # A tua lógica de "Com Barba" vira uma caixinha de marcar (Sim/Não)
    com_barba = models.BooleanField(default=False, verbose_name="Inclui Barba (+R$)?")
    
    forma_pagamento = models.CharField(max_length=20, choices=OPCOES_PAGAMENTO)
    
    # Valores Financeiros
    valor_total = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Valor Total (R$)")
    
    # Campos para Pagamento Misto (opcionais)
    valor_1 = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Parte 1 (Misto)")
    valor_2 = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Parte 2 (Misto)")
    
    criado_em = models.DateTimeField(auto_now_add=True) # Para saberes quando foi registrado

    def __str__(self):
        return f"{self.cliente} - {self.servico} ({self.barbeiro})"

class Saida(models.Model):
    data = models.DateField(default=date.today)
    descricao = models.CharField(max_length=200, verbose_name="Descrição da Despesa")
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    categoria = models.CharField(max_length=50, default="Geral")

    def __str__(self):
        return f"Saída: {self.descricao} - R$ {self.valor}"

class Venda(models.Model):
    data = models.DateField(default=date.today)
    item = models.CharField(max_length=200, verbose_name="Produto Vendido")
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    vendedor = models.CharField(max_length=50, choices=OPCOES_BARBEIROS)

    def __str__(self):
        return f"Venda: {self.item} - {self.vendedor}"