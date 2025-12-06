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
                
                # --- DADOS BÁSICOS ---
                data = request.POST.get('data')
                horario = request.POST.get('horario')
                cliente = request.POST.get('cliente').title() # Deixa nome bonito (Ex: João Silva)
                
                # CORREÇÃO 1: Nome do Barbeiro sem .upper()
                barbeiro = request.POST.get('barbeiro') 
                
                servico = request.POST.get('servico')
                com_barba = request.POST.get('com_barba')
                
                # Adiciona "+ Barba" se necessário
                if com_barba == 'on':
                    servico += " + Barba"

                # --- LÓGICA DO PAGAMENTO (CORREÇÃO DAS COLUNAS) ---
                pgt_form = request.POST.get('pagamento') # Vem "Misto", "Pix", etc.
                
                # Variáveis padrão (vazias) para não bagunçar a planilha
                v1 = "-"
                t1 = "-"
                v2 = "-"
                t2 = "-"
                valor_total = "0"

                if pgt_form == 'Misto':
                    # Se for Misto, preenche as variáveis com os dados reais
                    v1_raw = request.POST.get('valor_1', '0').replace(',', '.')
                    v2_raw = request.POST.get('valor_2', '0').replace(',', '.')
                    
                    v1 = v1_raw
                    v2 = v2_raw
                    t1 = request.POST.get('tipo_pagamento_1')
                    t2 = request.POST.get('tipo_pagamento_2')
                    
                    # Calcula total somando as partes
                    valor_total = float(v1_raw) + float(v2_raw)
                    
                    # Texto da coluna F (Forma de Pagamento Visual)
                    texto_pgt_visual = "Misto"
                    
                else:
                    # Se for Normal (Pix, Dinheiro, Cartão)
                    valor_raw = request.POST.get('valor', '0').replace(',', '.')
                    valor_total = float(valor_raw)
                    texto_pgt_visual = pgt_form # "Pix", "Dinheiro", etc.
                    
                    # CORREÇÃO 2: As variáveis v1, v2, t1, t2 continuam como "-"
                    # Isso garante que a planilha fica limpa nessas colunas

                # --- GRAVAÇÃO NA PLANILHA ---
                # A ordem aqui tem que ser sagrada para bater com o GET depois
                aba.append_row([
                    data,               # Coluna A
                    horario,            # Coluna B
                    cliente,            # Coluna C
                    servico,            # Coluna D
                    barbeiro,           # Coluna E (Agora correto: Lucas Borges)
                    texto_pgt_visual,   # Coluna F
                    v1,                 # Coluna G (Valor 1 ou -)
                    v2,                 # Coluna H (Valor 2 ou -)
                    valor_total,        # Coluna I (Total Geral)
                    "-",                # Coluna J (Reservado/Obs)
                    t1,                 # Coluna K (Tipo 1 ou -)
                    t2                  # Coluna L (Tipo 2 ou -)
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
    # 2. LER (GET)
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
                        while len(row) < 12: row.append("")

                        # Leitura do Valor Total (Coluna I - índice 8)
                        val_str = str(row[8]).replace(',', '.')
                        val = float(val_str) if val_str else 0.0
                        
                        # Leitura dos dados brutos
                        raw_barbeiro = str(row[4]).upper().strip() # Usamos upper aqui SÓ para contar os stats, não para exibir
                        raw_pgt = str(row[5]).upper().strip()
                        raw_servico = str(row[3]).strip()

                        # Identifica Barbeiros (Para os KPIs/Gráficos)
                        chave_barbeiro = 'OUTROS'
                        if 'LUCAS' in raw_barbeiro: chave_barbeiro = 'LUCAS'
                        elif 'ALUIZIO' in raw_barbeiro or 'ALUÍZIO' in raw_barbeiro: chave_barbeiro = 'ALUIZIO'
                        elif 'ERIK' in raw_barbeiro or 'ERICK' in raw_barbeiro: chave_barbeiro = 'ERIK'

                        # Item para a tabela visual (Expander)
                        item = {
                            'row_id': i + 1, 
                            'horario': row[1], 
                            'cliente': row[2], 
                            'servico': raw_servico, 
                            'barbeiro': row[4],  # Aqui pega o nome original da planilha (Lucas Borges)
                            'forma_pagamento': row[5], 
                            'valor_total': val,
                            'tipo_pagamento_1': row[10], 
                            'tipo_pagamento_2': row[11]
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
                        
                        # --- PAGAMENTOS (KPIs) ---
                        # Verifica se é Misto olhando se tem "/" ou se está escrito "Misto"
                        if '/' in raw_pgt or 'MISTO' in raw_pgt:
                            try:
                                v1 = float(str(row[6]).replace(',', '.') or 0) # Coluna G
                                v2 = float(str(row[7]).replace(',', '.') or 0) # Coluna H
                                t1 = str(row[10]).upper().strip() # Coluna K
                                t2 = str(row[11]).upper().strip() # Coluna L
                                
                                # Soma nos totais globais
                                if t1 in totais_pgt: totais_pgt[t1] += v1
                                if t2 in totais_pgt: totais_pgt[t2] += v2
                            except: pass
                        else:
                            # Pagamento normal
                            if 'PIX' in raw_pgt: totais_pgt['PIX'] += val
                            elif 'DINHEIRO' in raw_pgt: totais_pgt['DINHEIRO'] += val
                            elif 'CART' in raw_pgt: totais_pgt['CARTAO'] += val

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

    # Hora de Brasília
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
