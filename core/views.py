from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime, date
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONEXÃO ---
def conectar_google():
    try:
        caminho_local = 'credentials.json'
        caminho_render = '/etc/secrets/credentials.json'
        arquivo = caminho_local if os.path.exists(caminho_local) else caminho_render
        
        if not os.path.exists(arquivo): return None

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(arquivo, scope)
        client = gspread.authorize(creds)
        return client.open("Barbeariacontrole")
    except Exception as e:
        print(f"Erro Google: {e}")
        return None

# --- LOGIN ---
def login_view(request):
    if request.session.get('autenticado'): return redirect('home')
    if request.method == "POST":
        if request.POST.get('senha') == 'lb': 
            request.session['autenticado'] = True
            request.session.set_expiry(2592000) 
            return redirect('home')
        else: return render(request, 'login.html', {'erro': 'Senha incorreta!'})
    return render(request, 'login.html')

# --- HOME ---
def home(request):
    if not request.session.get('autenticado'): return redirect('login')
    data_filtro = request.GET.get('data_filtro', date.today().strftime('%Y-%m-%d'))

    # SALVAR (POST)
    if request.method == "POST":
        try:
            planilha = conectar_google()
            tipo_form = request.POST.get('tipo_formulario')

            if tipo_form == 'agendamento':
                aba = planilha.worksheet("Agendamentos")
                v1 = request.POST.get('valor_1', '0').replace(',', '.')
                v2 = request.POST.get('valor_2', '0').replace(',', '.')
                pgt = request.POST.get('pagamento')
                total = (float(v1) + float(v2)) if pgt == 'MISTO' else request.POST.get('valor', '0').replace(',', '.')
                
                aba.append_row([
                    request.POST.get('data'), 
                    request.POST.get('horario'), 
                    request.POST.get('cliente'), 
                    request.POST.get('servico'), 
                    request.POST.get('barbeiro'), 
                    pgt, v1, v2, total, 
                    "Sim" if request.POST.get('com_barba') == 'on' else "Não"
                ])
                messages.success(request, "Salvo no Google Sheets!")

            elif tipo_form == 'venda':
                aba = planilha.worksheet("Vendas")
                aba.append_row([
                    request.POST.get('data'),
                    request.POST.get('item'),
                    request.POST.get('valor', '0').replace(',', '.'),
                    request.POST.get('vendedor')
                ])
                messages.success(request, "Venda Salva!")

            elif tipo_form == 'saida':
                aba = planilha.worksheet("Saidas")
                aba.append_row([
                    request.POST.get('data'),
                    request.POST.get('descricao'),
                    request.POST.get('valor', '0').replace(',', '.')
                ])
                messages.warning(request, "Saída Salva!")

        except Exception as e: messages.error(request, f"Erro: {e}")
        return redirect('home')

    # LER DADOS (GET)
    agendamentos = []; vendas = []; saidas = []
    kpi_agend = 0; kpi_vend = 0; kpi_said = 0
    stats_barbeiros = {'LUCAS': 0, 'ALUIZIO': 0, 'ERIK': 0}
    totais_pgt = {'DINHEIRO': 0, 'PIX': 0, 'CARTAO': 0}
    stats_servicos = {}
    total_atendimentos = 0

    try:
        planilha = conectar_google()
        if planilha:
            # AGENDAMENTOS (Lê tudo e pega o número da linha 'i')
            # enumerate(..., 1) faz a contagem começar em 1 (linha 1 do Excel)
            rows_agend = planilha.worksheet("Agendamentos").get_all_values()
            for i, row in enumerate(rows_agend):
                if i == 0: continue # Pula cabeçalho
                if len(row) > 0 and row[0] == data_filtro:
                    try:
                        val = float(str(row[8]).replace(',', '.'))
                        # row_id = i + 1 (Porque o gspread conta a partir de 1)
                        item = {
                            'row_id': i + 1, 
                            'horario': row[1], 'cliente': row[2], 'servico': row[3],
                            'barbeiro': row[4], 'forma_pagamento': row[5], 'valor_total': val,
                            'com_barba': row[9] == "Sim" if len(row) > 9 else False
                        }
                        agendamentos.append(item)
                        kpi_agend += val
                        
                        # Gráficos
                        pts = 2 if (item['com_barba'] or item['servico'] == 'COMPLETO') else 1
                        if item['barbeiro'] in stats_barbeiros: stats_barbeiros[item['barbeiro']] += pts
                        total_atendimentos += pts
                        stats_servicos[item['servico']] = stats_servicos.get(item['servico'], 0) + 1
                        if item['forma_pagamento'] in totais_pgt: totais_pgt[item['forma_pagamento']] += val
                    except: pass
            
            agendamentos.sort(key=lambda x: x['horario'], reverse=True)

            # VENDAS
            rows_vend = planilha.worksheet("Vendas").get_all_values()
            for i, row in enumerate(rows_vend):
                if i == 0: continue
                if len(row) > 0 and row[0] == data_filtro:
                    try:
                        val = float(str(row[2]).replace(',', '.'))
                        vendas.append({'row_id': i + 1, 'item': row[1], 'valor': val, 'vendedor': row[3]})
                        kpi_vend += val
                    except: pass

            # SAIDAS
            rows_said = planilha.worksheet("Saidas").get_all_values()
            for i, row in enumerate(rows_said):
                if i == 0: continue
                if len(row) > 0 and row[0] == data_filtro:
                    try:
                        val = float(str(row[2]).replace(',', '.'))
                        saidas.append({'row_id': i + 1, 'descricao': row[1], 'valor': val})
                        kpi_said += val
                    except: pass

    except Exception as e: print(f"Erro leitura: {e}")

    kpi_lucro = (kpi_agend + kpi_vend) - kpi_said

    context = {
        'data_filtro': data_filtro,
        'agendamentos': agendamentos, 'vendas': vendas, 'saidas': saidas,
        'kpi_agend': kpi_agend, 'kpi_vend': kpi_vend, 'kpi_said': kpi_said, 'kpi_lucro': kpi_lucro,
        'stats_barbeiros': stats_barbeiros, 'total_atendimentos': total_atendimentos,
        'chart_pgt_labels': json.dumps(['Dinheiro', 'Pix', 'Cartão']),
        'chart_pgt_data': json.dumps([totais_pgt['DINHEIRO'], totais_pgt['PIX'], totais_pgt['CARTAO']]),
        'chart_barb_labels': json.dumps(list(stats_barbeiros.keys())),
        'chart_barb_data': json.dumps(list(stats_barbeiros.values())),
        'chart_serv_labels': json.dumps(list(stats_servicos.keys())),
        'chart_serv_data': json.dumps(list(stats_servicos.values())),
        'hora_agora': datetime.now().strftime("%H:%M")
    }
    return render(request, 'index.html', context)

# --- FUNÇÕES DE DELETAR (DIRETO NO SHEETS) ---
def deletar_item(request, tipo, row_id):
    if not request.session.get('autenticado'): return redirect('login')
    try:
        planilha = conectar_google()
        if tipo == 'agendamento': aba = planilha.worksheet("Agendamentos")
        elif tipo == 'venda': aba = planilha.worksheet("Vendas")
        elif tipo == 'saida': aba = planilha.worksheet("Saidas")
        
        aba.delete_rows(row_id) # O comando cirúrgico
        messages.warning(request, "Item apagado da planilha.")
    except Exception as e:
        messages.error(request, f"Erro ao apagar: {e}")
    return redirect('home')