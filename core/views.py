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
    # 1. SALVAR (POST) - Ajustado para tua Planilha
    # ==========================================
    if request.method == "POST":
        try:
            planilha = conectar_google()
            tipo_form = request.POST.get('tipo_formulario')

            if tipo_form == 'agendamento':
                aba = planilha.worksheet("Agendamentos")
                
                # Prepara valores
                v1 = request.POST.get('valor_1', '0').replace(',', '.')
                v2 = request.POST.get('valor_2', '0').replace(',', '.')
                pgt_principal = request.POST.get('pagamento')
                
                total = (float(v1) + float(v2)) if pgt_principal == 'MISTO' else request.POST.get('valor', '0').replace(',', '.')
                
                # ORDEM DE GRAVAÇÃO (Baseado na tua imagem + Novos Campos no final)
                # Col A(0): Data
                # Col B(1): Horário
                # Col C(2): Cliente
                # Col D(3): Serviço
                # Col E(4): Barbeiro
                # Col F(5): Pagamento
                # Col G(6): Valor 1
                # Col H(7): Valor 2
                # Col I(8): Valor Total (Aqui acaba a tua imagem atual)
                # --- NOVAS COLUNAS QUE SERÃO CRIADAS AUTOMATICAMENTE ---
                # Col J(9): Com Barba?
                # Col K(10): Tipo Pagamento 1
                # Col L(11): Tipo Pagamento 2

                aba.append_row([
                    request.POST.get('data'),       # A
                    request.POST.get('horario'),    # B
                    request.POST.get('cliente'),    # C
                    request.POST.get('servico'),    # D
                    request.POST.get('barbeiro'),   # E
                    pgt_principal,                  # F
                    v1,                             # G
                    v2,                             # H
                    total,                          # I
                    "Sim" if request.POST.get('com_barba') == 'on' else "Não", # J (Novo)
                    request.POST.get('tipo_pagamento_1', '-'), # K (Novo)
                    request.POST.get('tipo_pagamento_2', '-')  # L (Novo)
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
    # 2. LER (GET) - Corrigido para os Índices da Imagem
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
            # --- LER AGENDAMENTOS ---
            rows_agend = planilha.worksheet("Agendamentos").get_all_values()
            for i, row in enumerate(rows_agend):
                if i == 0: continue # Pula cabeçalho
                
                # Filtra pela data e garante que a linha tem dados mínimos
                if len(row) > 0 and row[0] == data_filtro:
                    try:
                        # Se a linha for antiga e curta (só até coluna I), preenche o resto com vazio
                        # Isso evita erro ao tentar ler as colunas novas (Barba/Tipos Pgt)
                        while len(row) < 12: row.append("")

                        # LEITURA DOS DADOS (Mapeamento Correto)
                        # row[8] é a Coluna I (Valor Total) na tua imagem
                        val_str = str(row[8]).replace(',', '.')
                        val = float(val_str) if val_str else 0.0
                        
                        item = {
                            'row_id': i + 1, 
                            'horario': row[1],   # Coluna B
                            'cliente': row[2],   # Coluna C
                            'servico': row[3],   # Coluna D
                            'barbeiro': row[4],  # Coluna E
                            'forma_pagamento': row[5], # Coluna F
                            'valor_total': val,
                            # Novas colunas (se existirem na linha)
                            'com_barba': row[9] == "Sim", 
                            'tipo_pagamento_1': row[10],
                            'tipo_pagamento_2': row[11]
                        }
                        agendamentos.append(item)
                        kpi_agend += val
                        
                        # --- ESTATÍSTICAS ---
                        # Contagem Barbeiros
                        b_nome = item['barbeiro'] if item['barbeiro'] else 'Outros'
                        if b_nome in stats_barbeiros:
                            # Se tiver barba OU for completo conta em dobro (lógica exemplo)
                            pts = 2 if (item['com_barba'] or 'COMPLETO' in item['servico'].upper()) else 1
                            stats_barbeiros[b_nome] += pts
                            total_atendimentos += pts
                        
                        # Contagem Serviços
                        s_nome = item['servico']
                        stats_servicos[s_nome] = stats_servicos.get(s_nome, 0) + 1
                        
                        # Contagem Pagamentos
                        pgt = item['forma_pagamento']
                        if pgt in totais_pgt: 
                            totais_pgt[pgt] += val

                    except Exception as e: 
                        # Printa no console do servidor para ajudar a debugar se der erro
                        print(f"Erro na linha {i+1}: {e}")
            
            agendamentos.sort(key=lambda x: x['horario'], reverse=True)

            # --- LER VENDAS ---
            rows_vend = planilha.worksheet("Vendas").get_all_values()
            for i, row in enumerate(rows_vend):
                if i == 0: continue
                if len(row) > 0 and row[0] == data_filtro:
                    try:
                        val = float(str(row[2]).replace(',', '.'))
                        vendas.append({'row_id': i + 1, 'item': row[1], 'valor': val, 'vendedor': row[3]})
                        kpi_vend += val
                    except: pass

            # --- LER SAÍDAS ---
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
