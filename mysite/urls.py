from django.contrib import admin
from django.urls import path
# IMPORTANTE: Adicionei esta linha abaixo para o TemplateView funcionar
from django.views.generic import TemplateView 
from core.views import home, login_view, deletar_item

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Login e Home
    path('login/', login_view, name='login'),
    path('', home, name='home'), # A home é a raiz
    
    # Rota para deletar itens
    path('deletar/<str:tipo>/<int:row_id>/', deletar_item, name='deletar_item'),
    
    # --- ROTAS PWA (Service Worker e Manifest) ---
    # Nota: Certifique-se de que manifest.json e sw.js estão na pasta 'templates'
    path('manifest.json', TemplateView.as_view(template_name='manifest.json', content_type='application/json')),
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript')),
]
