from django.contrib import admin
from .models import Agendamento, Saida, Venda

# Configuração bonita para os Agendamentos
@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    # O que aparece na lista (colunas)
    list_display = ('data', 'horario', 'cliente', 'barbeiro', 'servico', 'com_barba', 'valor_total', 'forma_pagamento')
    
    # Filtros laterais (barra direita)
    list_filter = ('data', 'barbeiro', 'forma_pagamento', 'com_barba')
    
    # Barra de pesquisa (podes pesquisar por nome do cliente)
    search_fields = ('cliente',)
    
    # Ordenação padrão (do mais recente para o mais antigo)
    ordering = ('-data', '-horario')

# Configuração para Saídas
@admin.register(Saida)
class SaidaAdmin(admin.ModelAdmin):
    list_display = ('data', 'descricao', 'valor', 'categoria')
    list_filter = ('data', 'categoria')
    search_fields = ('descricao',)

# Configuração para Vendas
@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('data', 'item', 'valor', 'vendedor')
    list_filter = ('data', 'vendedor')