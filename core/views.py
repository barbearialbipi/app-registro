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

    # ==========================================
    # 1. SALVAR (POST)
    # ==========================================
    if request.method == "POST":
        try:
            planilha = conectar_google()
            tipo_form = request.POST.get('tipo_formulario')

            if tipo_form == 'agendamento':
                aba = planilha.worksheet("Agendamentos")
                
                # --- PREPARA VALORES ---
                v1 = request.POST.get('valor_1', '0').replace(',', '.')
                v2 = request.POST.get('valor_2', '0').replace(',', '.')
                
                # --- LÓGICA DO PAGAMENTO NA PLANILHA ---
                # Pega o que veio do formulário ('MISTO', 'PIX', etc)
                pgt_form = request.POST.get('pagamento') 
                t1 = request.POST.get('tipo_pagamento_1', '').upper()
                t2 = request.POST.get('tipo_pagamento_2', '').upper()
                
                # Variável que vai ser escrita na Coluna F
                texto_final_coluna_F = pgt_form.upper()

                if pgt_form == 'MISTO':
                    # Se for misto, soma os valores e MUDA O TEXTO para "TIPO1/TIPO2"
                    total = float(v1) + float(v2)
                    texto_final_coluna_F = f"{t1}/{t2}" 
                else:
                    # Se não for misto, pega o valor cheio e mantém o texto normal (ex: PIX)
                    total = request.POST.get('valor', '0').replace(',', '.')

                # --- LÓGICA DA BARBA ---
                servico_nome = request.POST.get('servico')
                tem_barba = request.POST.get('com_barba') == 'on'
                
                if tem_barba:
                    servico_nome = f"{servico_nome} com Barba"

                # --- GRAVAÇÃO ---
                aba.append_row([
                    request.POST.get('data'),
                    request.POST.get('horario'),
                    request.POST.get('cliente'),
                    servico_nome,                         # Ex: "Social com Barba"
                    request.POST.get('barbeiro').upper(), 
                    texto_final_coluna_F,                 # Ex: "DINHEIRO/PIX" (Não escreve "MISTO")
                    v1, v2, total,
                    "-",
                    t1, t2 # Mantemos aqui para segurança do cálculo
                ])
                messages.success(request, "Agendamento salvo!")

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

                        val_str = str(row[8]).replace(',', '.')
                        val = float(val_str) if val_str else 0.0
                        
                        raw_barbeiro = str(row[4]).upper().strip()
                        raw_pgt = str(row[5]).upper().strip() # Aqui virá "DINHEIRO/PIX"
                        raw_servico = str(row[3]).strip()

                        # Identifica Barbeiros
                        chave_barbeiro = 'OUTROS'
                        if 'LUCAS' in raw_barbeiro: chave_barbeiro = 'LUCAS'
                        elif 'ALUIZIO' in raw_barbeiro or 'ALUÍZIO' in raw_barbeiro: chave_barbeiro = 'ALUIZIO'
                        elif 'ERIK' in raw_barbeiro or 'ERICK' in raw_barbeiro: chave_barbeiro = 'ERIK'
                        elif 'FABRICIO' in raw_barbeiro or 'FABRÍCIO' in raw_barbeiro: chave_barbeiro = 'FABRICIO'

                        item = {
                            'row_id': i + 1, 
                            'horario': row[1], 
                            'cliente': row[2], 
                            'servico': raw_servico, 
                            'barbeiro': row[4], 
                            'forma_pagamento': row[5], # Exibe o que está na planilha (DINHEIRO/PIX)
                            'valor_total': val,
                            'tipo_pagamento_1': row[10], # Precisamos disso pro HTML antigo não quebrar
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
                        
                        # --- GRÁFICO SERVIÇOS (SEPARADOS) ---
                        nome_serv_base = servico_upper.replace(' COM BARBA', '').replace('+ BARBA', '').strip()
                        stats_servicos[nome_serv_base] = stats_servicos.get(nome_serv_base, 0) + 1
                        if e_combo:
                            stats_servicos['BARBA'] = stats_servicos.get('BARBA', 0) + 1
                        
                        # --- PAGAMENTOS (GRÁFICO) ---
                        # Se encontrar uma barra, entende que é misto (ex: DINHEIRO/PIX)
                        if '/' in raw_pgt or 'MISTO' in raw_pgt:
                            try:
                                v1 = float(str(row[6]).replace(',', '.') or 0)
                                v2 = float(str(row[7]).replace(',', '.') or 0)
                                
                                # Tenta pegar os tipos das colunas K/L, se não, faz split do texto
                                t1 = str(row[10]).upper().strip()
                                t2 = str(row[11]).upper().strip()
                                
                                if not t1 and '/' in raw_pgt:
                                    partes = raw_pgt.split('/')
                                    t1 = partes[0].strip()
                                    t2 = partes[1].strip() if len(partes) > 1 else ''

                                if t1 in totais_pgt: totais_pgt[t1] += v1
                                if t2 in totais_pgt: totais_pgt[t2] += v2
                            except: pass
                        else:
                            if 'PIX' in raw_pgt: totais_pgt['PIX'] += val
                            elif 'DINHEIRO' in raw_pgt: totais_pgt['DINHEIRO'] += val
                            elif 'CART' in raw_pgt: totais_pgt['CARTAO'] += val

                    except Exception as e: 
                        print(f"Erro processar linha {i+1}: {e}")
            
            agendamentos.sort(key=lambda x: x['horario'], reverse=True)

            # (Vendas e Saídas inalteradas...)
            rows_vend = planilha.worksheet("Vendas").get_all_values()
            for i, row in enumerate(rows_vend):
                if i == 0: continue
                if len(row) > 0 and row[0] == data_filtro:
                    try:
                        val = float(str(row[2]).replace(',', '.'))
                        vendas.append({'row_id': i + 1, 'item': row[1], 'valor': val, 'vendedor': row[3]})
                        kpi_vend += val
                    except: pass

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
