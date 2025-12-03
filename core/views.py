from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Agendamento, Saida, Venda
from django.db.models import Sum
from datetime import datetime, date
import json

def home(request):
    # --- 1. SE FOR PARA SALVAR (POST) ---
    if request.method == "POST":
        data = request.POST.get('data')
        horario = request.POST.get('horario')
        cliente = request.POST.get('cliente')
        servico = request.POST.get('servico')
        barbeiro = request.POST.get('barbeiro')
        pagamento = request.POST.get('pagamento')
        com_barba = request.POST.get('com_barba') == 'on'
        
        # Lógica do Pagamento Misto ou Normal
        valor_total = 0
        v1 = 0
        v2 = 0
        
        if pagamento == 'MISTO':
            v1 = float(request.POST.get('valor_1', 0))
            v2 = float(request.POST.get('valor_2', 0))
            valor_total = v1 + v2
        else:
            valor_total = request.POST.get('valor')

        Agendamento.objects.create(
            data=data, horario=horario, cliente=cliente, servico=servico,
            barbeiro=barbeiro, forma_pagamento=pagamento,
            valor_total=valor_total, valor_1=v1, valor_2=v2, com_barba=com_barba
        )
        messages.success(request, f"Agendamento de {cliente} salvo!")
        return redirect('home')

    # --- 2. SE FOR PARA MOSTRAR A TELA (GET) ---
    
    # Define a data para filtrar (Padrão: Hoje)
    data_filtro = request.GET.get('data_filtro', date.today().strftime('%Y-%m-%d'))
    
    # Pega os dados do Banco filtrados por data
    agendamentos = Agendamento.objects.filter(data=data_filtro).order_by('-horario')
    saidas = Saida.objects.filter(data=data_filtro)
    vendas = Venda.objects.filter(data=data_filtro)

    # --- CÁLCULOS FINANCEIROS (KPIs) ---
    total_agendamentos = agendamentos.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
    total_vendas = vendas.aggregate(Sum('valor'))['valor__sum'] or 0
    total_saidas = saidas.aggregate(Sum('valor'))['valor__sum'] or 0
    lucro_liquido = (total_agendamentos + total_vendas) - total_saidas

    # --- DADOS PARA OS GRÁFICOS ---
    
    # 1. Pagamentos (Pix vs Dinheiro vs Cartão)
    # Precisamos somar manualmente por causa do misto
    pgt_pix = 0
    pgt_dinheiro = 0
    pgt_cartao = 0
    
    for a in agendamentos:
        if a.forma_pagamento == 'PIX': pgt_pix += float(a.valor_total)
        elif a.forma_pagamento == 'DINHEIRO': pgt_dinheiro += float(a.valor_total)
        elif a.forma_pagamento == 'CARTAO': pgt_cartao += float(a.valor_total)
        elif a.forma_pagamento == 'MISTO':
            # Assumindo simplificação: No misto, geralmente sabemos o que foi o que, 
            # mas aqui vamos dividir meio a meio ou precisaria de mais campos. 
            # Vou somar ao 'Dinheiro' e 'Pix' genericamente para o exemplo:
            pgt_dinheiro += float(a.valor_1)
            pgt_pix += float(a.valor_2)

    # 2. Contagem por Barbeiro (Regra: Com Barba conta 2)
    stats_barbeiros = {'LUCAS': 0, 'ALUIZIO': 0, 'ERIK': 0}
    for a in agendamentos:
        pontos = 2 if a.com_barba or a.servico == 'COMPLETO' else 1
        if a.barbeiro in stats_barbeiros:
            stats_barbeiros[a.barbeiro] += pontos

    # 3. Serviços mais realizados
    stats_servicos = {}
    for a in agendamentos:
        nome_servico = a.get_servico_display() # Pega o nome bonito
        stats_servicos[nome_servico] = stats_servicos.get(nome_servico, 0) + 1
        if a.com_barba:
            stats_servicos['Barba Adicional'] = stats_servicos.get('Barba Adicional', 0) + 1

    context = {
        'agendamentos': agendamentos,
        'data_filtro': data_filtro,
        'kpi_agendamentos': total_agendamentos,
        'kpi_saidas': total_saidas,
        'kpi_vendas': total_vendas,
        'kpi_lucro': lucro_liquido,
        # Dados convertidos para JSON para o Javascript ler
        'chart_pgt_labels': json.dumps(['Pix', 'Dinheiro', 'Cartão']),
        'chart_pgt_data': json.dumps([pgt_pix, pgt_dinheiro, pgt_cartao]),
        'chart_barbeiros_labels': json.dumps(list(stats_barbeiros.keys())),
        'chart_barbeiros_data': json.dumps(list(stats_barbeiros.values())),
        'chart_servicos_labels': json.dumps(list(stats_servicos.keys())),
        'chart_servicos_data': json.dumps(list(stats_servicos.values())),
        # Data atual para o formulário
        'hora_agora': datetime.now().strftime("%H:%M") 
    }
    return render(request, 'index.html', context)

def deletar_agendamento(request, id):
    item = get_object_or_404(Agendamento, id=id)
    item.delete()
    messages.warning(request, "Item apagado com sucesso.")
    return redirect('home')