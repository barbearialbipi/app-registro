from django.contrib import admin
from .models import Agendamento, Saida, Venda

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('data', 'horario', 'cliente', 'barbeiro', 'servico', 'valor_total', 'forma_pagamento')
    list_filter = ('data', 'barbeiro', 'forma_pagamento', 'com_barba')
    search_fields = ('cliente',)
    ordering = ('-data', '-horario')

@admin.register(Saida)
class SaidaAdmin(admin.ModelAdmin):
    # CORREÇÃO: Apenas Data, Descrição e Valor (Sem categoria)
    list_display = ('data', 'descricao', 'valor')
    list_filter = ('data',)
    search_fields = ('descricao',)

@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('data', 'item', 'valor', 'vendedor')
    list_filter = ('data', 'vendedor')