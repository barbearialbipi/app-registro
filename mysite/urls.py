from django.contrib import admin
from django.urls import path
from core.views import home, deletar_agendamento

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    # Nova rota: O <int:id> serve para o Django saber QUAL item apagar
    path('deletar/<int:id>/', deletar_agendamento, name='deletar_agendamento'),
]