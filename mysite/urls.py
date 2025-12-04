from django.contrib import admin
from django.urls import path
from core.views import home, login_view, deletar_item

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('', home, name='home'),
    
    # Rota mágica para deletar qualquer coisa do Sheets
    # Ex: /deletar/agendamento/54/ (Apaga linha 54 da aba Agendamentos)
    path('deletar/<str:tipo>/<int:row_id>/', deletar_item, name='deletar_item'),
]