import os
import subprocess
import sys


def run_command(command):
    """Executa um comando no terminal e mostra o resultado"""
    print(f"🔄 Executando: {command}")
    try:
        subprocess.check_call(command, shell=True)
        print("✅ Feito!")
    except subprocess.CalledProcessError:
        print(f"❌ Erro ao executar: {command}")
        sys.exit(1)


print("--- 🏗️ INICIANDO O CONSTRUTOR AUTOMÁTICO ---")

# 1. Instalar Django e Gunicorn (necessário para o Render)
run_command(f"{sys.executable} -m pip install django gunicorn")

# 2. Criar o Projeto Django (se ainda não existir)
if not os.path.exists("mysite"):
    run_command("django-admin startproject mysite .")
    run_command(f"{sys.executable} manage.py startapp core")
    print("🏠 Estrutura de pastas criada.")
else:
    print("🏠 A pasta 'mysite' já existe. Pulando criação.")

# 3. Criar arquivo requirements.txt (Lista de compras para o Render)
with open("requirements.txt", "w") as f:
    f.write("django\ngunicorn\n")
print("📝 requirements.txt criado.")

# 4. Modificar o settings.py para aceitar o Render
settings_path = os.path.join("mysite", "settings.py")
with open(settings_path, "r") as f:
    content = f.read()

# Troca o ALLOWED_HOSTS vazio por '*' (libera geral)
new_content = content.replace("ALLOWED_HOSTS = []", "ALLOWED_HOSTS = ['*']")

# Adiciona a app 'core' se não tiver
if "'core'," not in new_content:
    new_content = new_content.replace(
        "INSTALLED_APPS = [", "INSTALLED_APPS = [\n    'core',"
    )

with open(settings_path, "w") as f:
    f.write(new_content)
print("⚙️ settings.py configurado para a nuvem.")

# 5. Criar um modelo básico no core/models.py para testar
models_code = """from django.db import models

class Agendamento(models.Model):
    cliente = models.CharField(max_length=100)
    data = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.cliente
"""
with open(os.path.join("core", "models.py"), "w") as f:
    f.write(models_code)

print("\n--- 🎉 SUCESSO! ---")
print("O teu projeto Django foi criado.")
print("Agora, basta enviar para o GitHub.")
