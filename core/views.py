from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Agendamento, Saida, Venda
from django.db.models import Sum
from datetime import datetime, date
import json

def home(request):
    # --- 1. RECEBER DADOS (POST) ---
    if request.method == "POST":
        tipo_form = request.POST.get('tipo_formulario')

        # AGENDAMENTO
        if tipo_form == 'agendamento':
            data = request.POST.get('data')
            horario = request.POST.get('horario')
            cliente = request.POST.get('cliente')
            servico = request.POST.get('servico')
            barbeiro = request.POST.get('barbeiro')
            pagamento = request.POST.get('pagamento')
            com_barba = request.POST.get('com_barba') == 'on'
            
            # Lógica Mista
            v1 = 0; tipo1 = None; v2 = 0; tipo2 = None; valor_total = 0

            if pagamento == 'MISTO':
                try:
                    v1 = float(request.POST.get('valor_1', '0').replace(',', '.'))
                    tipo1 = request.POST.get('tipo_pagamento_1')
                    v2 = float(request.POST.get('valor_2', '0').replace(',', '.'))
                    tipo2 = request.POST.get('tipo_pagamento_2')
                    valor_total = v1 + v2
                except ValueError: valor_total = 0
            else:
                try: valor_total = float(request.POST.get('valor', '0').replace(',', '.'))
                except ValueError: valor_total = 0

            Agendamento.objects.create(
                data=data, horario=horario, cliente=cliente, servico=servico,
                barbeiro=barbeiro, forma_pagamento=pagamento,
                valor_total=valor_total, com_barba=com_barba,
                valor_1=v1, tipo_pagamento_1=tipo1, valor_2=v2, tipo_pagamento_2=tipo2
            )
            messages.success(request, f"Agendamento de {cliente} salvo!")

        # VENDA
        elif tipo_form == 'venda':
            try:
                Venda.objects.create(
                    data=request.POST.get('data'),
                    item=request.POST.get('item'),
                    valor=float(request.POST.get('valor', '0').replace(',', '.')),
                    vendedor=request.POST.get('vendedor')
                )
                messages.success(request, "Venda registrada!")
            except ValueError: messages.error(request, "Erro no valor.")

        # SAÍDA
        elif tipo_form == 'saida':
            try:
                Saida.objects.create(
                    data=request.POST.get('data'),
                    descricao=request.POST.get('descricao'),
                    valor=float(request.POST.get('valor', '0').replace(',', '.'))
                )
                messages.warning(request, "Saída registrada.")
            except ValueError: messages.error(request, "Erro no valor.")

        return redirect('home')

    # --- 2. EXIBIR DADOS (GET) ---
    data_filtro = request.GET.get('data_filtro', date.today().strftime('%Y-%m-%d'))
    
    agendamentos = Agendamento.objects.filter(data=data_filtro).order_by('-horario')
    saidas = Saida.objects.filter(data=data_filtro).order_by('-id')
    vendas = Venda.objects.filter(data=data_filtro).order_by('-id')

    # KPIs Financeiros
    total_agend = agendamentos.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    total_vend = vendas.aggregate(Sum('valor'))['valor__sum'] or 0
    total_said = saidas.aggregate(Sum('valor'))['valor__sum'] or 0
    lucro = (total_agend + total_vend) - total_said

    # Gráfico Pagamentos
    totais_pgt = {'DINHEIRO': 0, 'PIX': 0, 'CARTAO': 0}
    for a in agendamentos:
        if a.forma_pagamento == 'MISTO':
            if a.tipo_pagamento_1 in totais_pgt: totais_pgt[a.tipo_pagamento_1] += float(a.valor_1)
            if a.tipo_pagamento_2 in totais_pgt: totais_pgt[a.tipo_pagamento_2] += float(a.valor_2)
        elif a.forma_pagamento in totais_pgt:
            totais_pgt[a.forma_pagamento] += float(a.valor_total)

    # --- ESTATÍSTICAS DE BARBEIROS (PRODUTIVIDADE) ---
    # Inicializamos com 0 para garantir que todos apareçam
    stats_barbeiros = {'LUCAS': 0, 'ALUIZIO': 0, 'ERIK': 0}
    total_atendimentos_dia = 0 # Variável para a soma total
    
    stats_servicos = {}

    for a in agendamentos:
        # Regra: Com Barba ou Combo = 2 pontos, Resto = 1 ponto
        pts = 2 if a.com_barba or a.servico == 'COMPLETO' else 1
        
        if a.barbeiro in stats_barbeiros:
            stats_barbeiros[a.barbeiro] += pts
        
        total_atendimentos_dia += pts # Soma no geral

        # Stats Serviços
        stats_servicos[a.get_servico_display()] = stats_servicos.get(a.get_servico_display(), 0) + 1

    context = {
        'agendamentos': agendamentos, 'saidas': saidas, 'vendas': vendas,
        'data_filtro': data_filtro,
        'kpi_agend': total_agend, 'kpi_vend': total_vend, 'kpi_said': total_said, 'kpi_lucro': lucro,
        
        # Passamos os dados de produtividade para o template
        'stats_barbeiros': stats_barbeiros,
        'total_atendimentos': total_atendimentos_dia,

        'chart_pgt_labels': json.dumps(['Dinheiro', 'Pix', 'Cartão']),
        'chart_pgt_data': json.dumps([totais_pgt['DINHEIRO'], totais_pgt['PIX'], totais_pgt['CARTAO']]),
        'chart_barb_labels': json.dumps(list(stats_barbeiros.keys())),
        'chart_barb_data': json.dumps(list(stats_barbeiros.values())),
        'chart_serv_labels': json.dumps(list(stats_servicos.keys())),
        'chart_serv_data': json.dumps(list(stats_servicos.values())),
        'hora_agora': datetime.now().strftime("%H:%M")
    }
    return render(request, 'index.html', context)

# Deletes (iguais)
def deletar_agendamento(request, id): get_object_or_404(Agendamento, id=id).delete(); return redirect('home')
def deletar_venda(request, id): get_object_or_404(Venda, id=id).delete(); return redirect('home')
def deletar_saida(request, id): get_object_or_404(Saida, id=id).delete(); return redirect('home')