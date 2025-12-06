from django.shortcuts import render, redirect
from django.contrib import messages
# --- ALTERAÇÃO 1: Adicionei 'timedelta' aqui nos imports ---
from datetime import datetime, date, timedelta
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

    # ==========================================
    # 1. SALVAR (POST)
    # ==========================================
    if request.method == "POST":
        try:
            planilha = conectar_google()
            tipo_form = request.POST.get('tipo_formulario')

            if tipo_form == 'agendamento':
                aba = planilha.worksheet("Agendamentos")
                
                # Dados Básicos
                data = request.POST.get('data')
                horario = request.POST.get('horario')
                cliente = request.POST.get('cliente').title()
                barbeiro = request.POST.get('barbeiro') # Nome correto (Ex: Lucas Borges)
                
                servico = request.POST.get('servico')
                if request.POST.get('com_barba') == 'on':
                    servico += " + Barba"

                # --- LÓGICA DO PAGAMENTO (NOVA E SIMPLIFICADA) ---
                pgt_raw = request.POST.get('pagamento') # "Misto" ou "Pix"...
                
                # Variáveis padrão (para limpar a planilha se não for misto)
                v1 = "-"
                v2 = "-"
                valor_total = 0.0
                texto_final_coluna_F = ""

                if pgt_raw == 'Misto':
                    # Pega os tipos e valores
                    t1 = request.POST.get('tipo_pagamento_1')
                    t2 = request.POST.get('tipo_pagamento_2')
                    v1_str = request.POST.get('valor_1', '0').replace(',', '.')
                    v2_str = request.POST.get('valor_2', '0').replace(',', '.')
                    
                    v1 = float(v1_str)
                    v2 = float(v2_str)
                    valor_total = v1 + v2
                    
                    # AQUI ESTÁ O QUE VOCÊ PEDIU:
                    # Coluna F fica: "Dinheiro/Pix"
                    texto_final_coluna_F = f"{t1}/{t2}"
                    
                else:
                    # Pagamento Normal
                    valor_str = request.POST.get('valor', '0').replace(',', '.')
                    valor_total = float(valor_str)
                    
                    # Coluna F fica apenas: "Pix" (ou o que for)
                    texto_final_coluna_F = pgt_raw

                # --- GRAVAÇÃO NA PLANILHA (SÓ ATÉ A COLUNA I) ---
                aba.append_row([
                    data,               # A
                    horario,            # B
                    cliente,            # C
                    servico,            # D
                    barbeiro,           # E
                    texto_final_coluna_F, # F (Ex: "Dinheiro/Pix" ou "Dinheiro")
                    v1,                 # G (Valor 1 ou -)
                    v2,                 # H (Valor 2 ou -)
                    valor_total         # I (Total)
                    # J, K, L... NÃO EXISTEM MAIS
                ])
                messages.success(request, "Agendamento salvo com sucesso!")

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

        except Exception as e: messages.error(request, f"Erro ao salvar: {e}")
        return redirect('home')

    # ==========================================
    # 2. LER (GET) - LÓGICA ATUALIZADA PARA NOVA PLANILHA
    # ==========================================
    agendamentos = []; vendas = []; saidas = []
    kpi_agend = 0; kpi_vend = 0; kpi_said = 0
    
    stats_barbeiros = {'LUCAS': 0, 'ALUIZIO': 0, 'ERIK': 0}
    totais_pgt = {'DINHEIRO': 0, 'PIX': 0, 'CARTAO': 0}
    stats_servicos = {}
    total_atendimentos = 0

    try:
        planilha = conectar_google()
        if planilha:
            rows_agend = planilha.worksheet("Agendamentos").get_all_values()
            for i, row in enumerate(rows_agend):
                if i == 0: continue 
                
                if len(row) > 0 and row[0] == data_filtro:
                    try:
                        # Garante que tem colunas suficientes (até I/8)
                        while len(row) < 9: row.append("")

                        # Valor Total (Coluna I -> índice 8)
                        val_str = str(row[8]).replace(',', '.')
                        val = float(val_str) if val_str else 0.0
                        
                        raw_barbeiro = str(row[4]).upper().strip()
                        raw_pgt = str(row[5]).strip() # Ex: "Dinheiro/Pix" ou "Pix"
                        raw_servico = str(row[3]).strip()

                        # Identifica Barbeiros
                        chave_barbeiro = 'OUTROS'
                        if 'LUCAS' in raw_barbeiro: chave_barbeiro = 'LUCAS'
                        elif 'ALUIZIO' in raw_barbeiro or 'ALUÍZIO' in raw_barbeiro: chave_barbeiro = 'ALUIZIO'
                        elif 'ERIK' in raw_barbeiro or 'ERICK' in raw_barbeiro: chave_barbeiro = 'ERIK'
                        
                        # Lista Visual
                        item = {
                            'row_id': i + 1, 
                            'horario': row[1], 
                            'cliente': row[2], 
                            'servico': raw_servico, 
                            'barbeiro': row[4], 
                            'forma_pagamento': raw_pgt, # Mostra "Dinheiro/Pix" na lista
                            'valor_total': val,
                            'tipo_pagamento_1': '', # Não usamos mais essas visualmente na lista rápida
                            'tipo_pagamento_2': ''
                        }
                        agendamentos.append(item)
                        kpi_agend += val
                        
                        # --- CÁLCULO PONTOS BARBEIRO ---
                        servico_upper = raw_servico.upper()
                        e_combo = ('COM BARBA' in servico_upper) or ('+ BARBA' in servico_upper) or ('COMPLETO' in servico_upper)
                        
                        if chave_barbeiro in stats_barbeiros:
                            pts = 2 if e_combo else 1
                            stats_barbeiros[chave_barbeiro] += pts
                            total_atendimentos += pts
                        
                        # --- GRÁFICO SERVIÇOS ---
                        nome_serv_base = servico_upper.replace(' COM BARBA', '').replace('+ BARBA', '').strip()
                        stats_servicos[nome_serv_base] = stats_servicos.get(nome_serv_base, 0) + 1
                        if e_combo:
                            stats_servicos['BARBA'] = stats_servicos.get('BARBA', 0) + 1
                        
                        # --- PAGAMENTOS (KPIs - LÓGICA NOVA) ---
                        # Agora lemos a Coluna F para saber os tipos
                        # E as colunas G e H para saber os valores
                        
                        pgt_upper = raw_pgt.upper()
                        
                        if '/' in raw_pgt: 
                            # É MISTO (Ex: "Dinheiro/Pix")
                            partes = raw_pgt.split('/')
                            tipo1 = partes[0].strip().upper()
                            tipo2 = partes[1].strip().upper() if len(partes) > 1 else ''
                            
                            try:
                                v1 = float(str(row[6]).replace(',', '.') or 0) # Coluna G
                                v2 = float(str(row[7]).replace(',', '.') or 0) # Coluna H
                                
                                # Soma nos totais
                                if tipo1 in totais_pgt: totais_pgt[tipo1] += v1
                                else:
                                    if 'PIX' in tipo1: totais_pgt['PIX'] += v1
                                    elif 'DINHEIRO' in tipo1: totais_pgt['DINHEIRO'] += v1
                                    elif 'CART' in tipo1: totais_pgt['CARTAO'] += v1

                                if tipo2 in totais_pgt: totais_pgt[tipo2] += v2
                                else:
                                    if 'PIX' in tipo2: totais_pgt['PIX'] += v2
                                    elif 'DINHEIRO' in tipo2: totais_pgt['DINHEIRO'] += v2
                                    elif 'CART' in tipo2: totais_pgt['CARTAO'] += v2
                                    
                            except: pass
                        else:
                            # Pagamento normal (Ex: "Pix")
                            if 'PIX' in pgt_upper: totais_pgt['PIX'] += val
                            elif 'DINHEIRO' in pgt_upper: totais_pgt['DINHEIRO'] += val
                            elif 'CART' in pgt_upper: totais_pgt['CARTAO'] += val

                    except Exception as e: 
                        print(f"Erro processar linha {i+1}: {e}")
            
            agendamentos.sort(key=lambda x: x['horario'], reverse=True)

            # --- VENDAS ---
            rows_vend = planilha.worksheet("Vendas").get_all_values()
            for i, row in enumerate(rows_vend):
                if i == 0: continue
                if len(row) > 0 and row[0] == data_filtro:
                    try:
                        val = float(str(row[2]).replace(',', '.'))
                        vendas.append({'row_id': i + 1, 'item': row[1], 'valor': val, 'vendedor': row[3]})
                        kpi_vend += val
                    except: pass

            # --- SAIDAS ---
            rows_said = planilha.worksheet("Saidas").get_all_values()
            for i, row in enumerate(rows_said):
                if i == 0: continue
                if len(row) > 0 and row[0] == data_filtro:
                    try:
                        val = float(str(row[2]).replace(',', '.'))
                        saidas.append({'row_id': i + 1, 'descricao': row[1], 'valor': val})
                        kpi_said += val
                    except: pass

    except Exception as e: print(f"Erro leitura geral: {e}")

    kpi_lucro = (kpi_agend + kpi_vend) - kpi_said

    hora_brasilia = (datetime.utcnow() - timedelta(hours=3)).strftime("%H:%M")

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
        'hora_agora': hora_brasilia 
    }
    return render(request, 'index.html', context)

# --- DELETAR ---
def deletar_item(request, tipo, row_id):
    if not request.session.get('autenticado'): return redirect('login')
    try:
        planilha = conectar_google()
        if tipo == 'agendamento': aba = planilha.worksheet("Agendamentos")
        elif tipo == 'venda': aba = planilha.worksheet("Vendas")
        elif tipo == 'saida': aba = planilha.worksheet("Saidas")
        
        aba.delete_rows(row_id)
        messages.warning(request, "Item apagado com sucesso.")
    except Exception as e:
        messages.error(request, f"Erro ao apagar: {e}")
    return redirect('home')
