from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Agendamento, Saida, Venda
from django.db.models import Sum
from datetime import datetime, date
import json
import os

# --- IMPORTAÇÕES DO GOOGLE SHEETS ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def salvar_no_sheets(nome_aba, dados_linha):
    """
    Função auxiliar para conectar e salvar no Google Sheets.
    Procura o credentials.json na pasta atual ou em /etc/secrets/ (padrão Render)
    """
    try:
        # Tenta achar o arquivo no local padrão ou na pasta de segredos do Render
        caminho_local = 'credentials.json'
        caminho_render = '/etc/secrets/credentials.json'
        
        arquivo_final = caminho_local if os.path.exists(caminho_local) else caminho_render
        
        # Se não achar em lugar nenhum, desiste (evita erro fatal no site)
        if not os.path.exists(arquivo_final):
            print(f"⚠️ Aviso: credentials.json não encontrado em {arquivo_final}")
            return False

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(arquivo_final, scope)
        client = gspread.authorize(creds)

        # ATUALIZADO: Nome da planilha corrigido para "Barbeariacontrole"
        sheet = client.open("Barbeariacontrole") 
        aba = sheet.worksheet(nome_aba) # Seleciona a aba (Agendamentos, Vendas, Saidas)
        
        aba.append_row(dados_linha)
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar no Google Sheets: {e}")
        return False

# --- FUNÇÕES DE LOGIN E HOME ---

def login_view(request):
    if request.session.get('autenticado'): return redirect('home')
    if request.method == "POST":
        if request.POST.get('senha') == 'lb': 
            request.session['autenticado'] = True
            request.session.set_expiry(2592000) 
            return redirect('home')
        else: return render(request, 'login.html', {'erro': 'Senha incorreta!'})
    return render(request, 'login.html')

def home(request):
    if not request.session.get('autenticado'): return redirect('login')

    if request.method == "POST":
        tipo_form = request.POST.get('tipo_formulario')

        # >>> AGENDAMENTO
        if tipo_form == 'agendamento':
            try:
                data = request.POST.get('data')
                horario = request.POST.get('horario')
                cliente = request.POST.get('cliente')
                servico = request.POST.get('servico')
                barbeiro = request.POST.get('barbeiro')
                pagamento = request.POST.get('pagamento')
                com_barba = request.POST.get('com_barba') == 'on'
                
                v1 = 0; tipo1 = None; v2 = 0; tipo2 = None; valor_total = 0

                if pagamento == 'MISTO':
                    v1 = float(request.POST.get('valor_1', '0').replace(',', '.'))
                    tipo1 = request.POST.get('tipo_pagamento_1')
                    v2 = float(request.POST.get('valor_2', '0').replace(',', '.'))
                    tipo2 = request.POST.get('tipo_pagamento_2')
                    valor_total = v1 + v2
                else:
                    valor_total = float(request.POST.get('valor', '0').replace(',', '.'))

                # 1. Salvar no Django
                Agendamento.objects.create(
                    data=data, horario=horario, cliente=cliente, servico=servico,
                    barbeiro=barbeiro, forma_pagamento=pagamento,
                    valor_total=valor_total, com_barba=com_barba,
                    valor_1=v1, tipo_pagamento_1=tipo1, valor_2=v2, tipo_pagamento_2=tipo2
                )
                
                # 2. Salvar no Google Sheets (Aba: Agendamentos)
                # Colunas: Data, Horário, Cliente, Serviço, Barbeiro, Pagamento, Valor 1, Valor 2, Valor Total
                dados_gs = [
                    data, horario, cliente, servico, barbeiro, pagamento, 
                    v1 if pagamento == 'MISTO' else 0, 
                    v2 if pagamento == 'MISTO' else 0, 
                    valor_total
                ]
                salvar_no_sheets("Agendamentos", dados_gs)

                messages.success(request, f"Agendamento salvo!")
            except: messages.error(request, "Erro ao salvar agendamento.")

        # >>> VENDA
        elif tipo_form == 'venda':
            try:
                data = request.POST.get('data')
                item = request.POST.get('item')
                val = float(request.POST.get('valor', '0').replace(',', '.'))
                vend = request.POST.get('vendedor')

                # Django
                Venda.objects.create(data=data, item=item, valor=val, vendedor=vend)
                
                # Google Sheets (Aba: Vendas) -> Data, Item, Valor, Vendedor
                salvar_no_sheets("Vendas", [data, item, val, vend])
                
                messages.success(request, "Venda registrada!")
            except: messages.error(request, "Erro ao salvar venda.")

        # >>> SAÍDA
        elif tipo_form == 'saida':
            try:
                data = request.POST.get('data')
                desc = request.POST.get('descricao')
                val = float(request.POST.get('valor', '0').replace(',', '.'))

                # Django
                Saida.objects.create(data=data, descricao=desc, valor=val)
                
                # Google Sheets (Aba: Saidas) -> Data, Descrição, Valor
                salvar_no_sheets("Saidas", [data, desc, val])

                messages.warning(request, "Saída registrada.")
            except: messages.error(request, "Erro ao salvar saída.")

        return redirect('home')

    # --- EXIBIÇÃO (GET) ---
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
    stats_barbeiros = {'LUCAS': 0, 'ALUIZIO': 0, 'ERIK': 0}
    total_atendimentos_dia = 0 
    stats_servicos = {}

    for a in agendamentos:
        # Pagamento
        if a.forma_pagamento == 'MISTO':
            if a.tipo_pagamento_1 in totais_pgt: totais_pgt[a.tipo_pagamento_1] += float(a.valor_1)
            if a.tipo_pagamento_2 in totais_pgt: totais_pgt[a.tipo_pagamento_2] += float(a.valor_2)
        elif a.forma_pagamento in totais_pgt:
            totais_pgt[a.forma_pagamento] += float(a.valor_total)
        
        # Produtividade
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

# Deletes
def deletar_agendamento(request, id):
    if request.session.get('autenticado'): get_object_or_404(Agendamento, id=id).delete()
    return redirect('home')
def deletar_venda(request, id):
    if request.session.get('autenticado'): get_object_or_404(Venda, id=id).delete()
    return redirect('home')
def deletar_saida(request, id):
    if request.session.get('autenticado'): get_object_or_404(Saida, id=id).delete()
    return redirect('home')