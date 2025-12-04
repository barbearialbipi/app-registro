from datetime import datetime
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.conf import settings

class AutoLogoutSemanalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Só verifica se o usuário estiver logado
        if request.user.is_authenticated:
            # Pega o número da semana atual (Domingo inicia nova semana)
            semana_atual = datetime.now().strftime("%U")
            
            # Pega a semana que está gravada na sessão do usuário
            semana_da_sessao = request.session.get('semana_login')

            # CENÁRIO 1: A semana mudou? (Era semana 40, agora é 41)
            if semana_da_sessao and semana_da_sessao != semana_atual:
                logout(request) # Chuta o usuário para fora
                return redirect(settings.LOGIN_URL) # Manda para o login

            # CENÁRIO 2: Acabou de logar ou não tem semana gravada? Grava a atual.
            if not semana_da_sessao:
                request.session['semana_login'] = semana_atual

        response = self.get_response(request)
        return response
