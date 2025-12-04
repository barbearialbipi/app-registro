from django.contrib import admin
from django.urls import path
from core.views import home, login_view, deletar_agendamento, deletar_venda, deletar_saida

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'), # Rota da porta de entrada
    path('', home, name='home'),
    
    # Rotas de ação
    path('deletar/agendamento/<int:id>/', deletar_agendamento, name='deletar_agendamento'),
    path('deletar/venda/<int:id>/', deletar_venda, name='deletar_venda'),
    path('deletar/saida/<int:id>/', deletar_saida, name='deletar_saida'),
]