from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Agendamento, Saida, Venda
from django.db.models import Sum
from datetime import datetime, date
import json

# --- 1. FUNÇÃO DE LOGIN (A ÚNICA QUE PEDE SENHA) ---
def login_view(request):
    # Se já tiver a "pulseira" (sessão), manda direto para a home
    if request.session.get('autenticado'):
        return redirect('home')

    if request.method == "POST":
        senha = request.POST.get('senha')
        
        # VERIFICAÇÃO DA SENHA (SÓ AQUI)
        if senha == 'lb': 
            request.session['autenticado'] = True # Dá a pulseira
            # Define que a sessão dura 1 mês (para não pedir senha toda hora no celular)
            request.session.set_expiry(2592000) 
            return redirect('home')
        else:
            return render(request, 'login.html', {'erro': 'Senha incorreta!'})
    
    return render(request, 'login.html')

# --- 2. FUNÇÃO PRINCIPAL (PROTEGIDA PELA SESSÃO) ---
def home(request):
    # SEGURANÇA: Se não tiver logado, chuta para o login
    if not request.session.get('autenticado'):
        return redirect('login')

    # --- LÓGICA DE SALVAR (POST) ---
    if request.method == "POST":
        tipo_form = request.POST.get('tipo_formulario')

        # AGENDAMENTO
        if tipo_form == 'agendamento':
            try:
                # Lógica Mista
                v1 = 0; tipo1 = None; v2 = 0; tipo2 = None; valor_total = 0
                pagamento = request.POST.get('pagamento')

                if pagamento == 'MISTO':
                    v1 = float(request.POST.get('valor_1', '0').replace(',', '.'))
                    tipo1 = request.POST.get('tipo_pagamento_1')
                    v2 = float(request.POST.get('valor_2', '0').replace(',', '.'))
                    tipo2 = request.POST.get('tipo_pagamento_2')
                    valor_total = v1 + v2
                else:
                    valor_total = float(request.POST.get('valor', '0').replace(',', '.'))

                Agendamento.objects.create(
                    data=request.POST.get('data'), 
                    horario=request.POST.get('horario'), 
                    cliente=request.POST.get('cliente'), 
                    servico=request.POST.get('servico'),
                    barbeiro=request.POST.get('barbeiro'), 
                    forma_pagamento=pagamento,
                    valor_total=valor_total, 
                    com_barba=request.POST.get('com_barba') == 'on',
                    valor_1=v1, tipo_pagamento_1=tipo1, valor_2=v2, tipo_pagamento_2=tipo2
                )
                messages.success(request, f"Agendamento salvo!")
            except: messages.error(request, "Erro ao salvar agendamento.")

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
            except: messages.error(request, "Erro ao salvar venda.")

        # SAÍDA
        elif tipo_form == 'saida':
            try:
                Saida.objects.create(
                    data=request.POST.get('data'),
                    descricao=request.POST.get('descricao'),
                    valor=float(request.POST.get('valor', '0').replace(',', '.'))
                )
                messages.warning(request, "Saída registrada.")
            except: messages.error(request, "Erro ao salvar saída.")

        return redirect('home')

    # --- LÓGICA DE EXIBIÇÃO (GET) ---
    data_filtro = request.GET.get('data_filtro', date.today().strftime('%Y-%m-%d'))
    
    agendamentos = Agendamento.objects.filter(data=data_filtro).order_by('-horario')
    saidas = Saida.objects.filter(data=data_filtro).order_by('-id')
    vendas = Venda.objects.filter(data=data_filtro).order_by('-id')

    # KPIs
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

    # Produtividade
    stats_barbeiros = {'LUCAS': 0, 'ALUIZIO': 0, 'ERIK': 0}
    total_atendimentos_dia = 0 
    stats_servicos = {}

    for a in agendamentos:
        pts = 2 if a.com_barba or a.servico == 'COMPLETO' else 1
        if a.barbeiro in stats_barbeiros: stats_barbeiros[a.barbeiro] += pts
        total_atendimentos_dia += pts
        stats_servicos[a.get_servico_display()] = stats_servicos.get(a.get_servico_display(), 0) + 1

    context = {
        'agendamentos': agendamentos, 'saidas': saidas, 'vendas': vendas,
        'data_filtro': data_filtro,
        'kpi_agend': total_agend, 'kpi_vend': total_vend, 'kpi_said': total_said, 'kpi_lucro': lucro,
        'stats_barbeiros': stats_barbeiros, 'total_atendimentos': total_atendimentos_dia,
        'chart_pgt_labels': json.dumps(['Dinheiro', 'Pix', 'Cartão']),
        'chart_pgt_data': json.dumps([totais_pgt['DINHEIRO'], totais_pgt['PIX'], totais_pgt['CARTAO']]),
        'chart_barb_labels': json.dumps(list(stats_barbeiros.keys())),
        'chart_barb_data': json.dumps(list(stats_barbeiros.values())),
        'chart_serv_labels': json.dumps(list(stats_servicos.keys())),
        'chart_serv_data': json.dumps(list(stats_servicos.values())),
        'hora_agora': datetime.now().strftime("%H:%M")
    }
    return render(request, 'index.html', context)

# --- FUNÇÕES DELETAR (NÃO PEDEM SENHA, SÓ CONFEREM A SESSÃO) ---
def deletar_agendamento(request, id):
    if request.session.get('autenticado'): # Verifica se está logado
        get_object_or_404(Agendamento, id=id).delete()
    return redirect('home')

def deletar_venda(request, id):
    if request.session.get('autenticado'):
        get_object_or_404(Venda, id=id).delete()
    return redirect('home')

def deletar_saida(request, id):
    if request.session.get('autenticado'):
        get_object_or_404(Saida, id=id).delete()
    return redirect('home')