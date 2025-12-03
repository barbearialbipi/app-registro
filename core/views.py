from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Agendamento

def home(request):
    # Se o usuário clicou no botão "Salvar" (Enviou o formulário)
    if request.method == "POST":
        cliente = request.POST.get('cliente')
        servico = request.POST.get('servico')
        barbeiro = request.POST.get('barbeiro')
        pagamento = request.POST.get('pagamento')
        valor = request.POST.get('valor')
        
        # Verifica se marcou a caixinha "Com Barba"
        com_barba = request.POST.get('com_barba') == 'on'

        # Salva no Banco de Dados
        Agendamento.objects.create(
            cliente=cliente,
            servico=servico,
            barbeiro=barbeiro,
            forma_pagamento=pagamento,
            valor_total=valor,
            com_barba=com_barba
        )
        
        # Mensagem de sucesso e recarrega a página limpa
        messages.success(request, f"Agendamento de {cliente} salvo com sucesso!")
        return redirect('home')

    # Se apenas acessou a página, mostra o arquivo HTML
    return render(request, 'index.html')
