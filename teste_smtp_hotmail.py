import smtplib
from email.mime.text import MIMEText
from getpass import getpass

# Configuração Moderna Outlook
SMTP_SERVER = 'smtp.office365.com'
SMTP_PORT = 587
EMAIL = 'nivioricardo@hotmail.com'

# Obtenha a senha de forma segura
PASSWORD = getpass("Cole a SENHA DE APLICATIVO gerada (não a senha normal): ")

try:
    # Prepara mensagem
    msg = MIMEText('Teste de conexão SMTP moderno')
    msg['Subject'] = 'Teste Hotmail Modern Auth'
    msg['From'] = EMAIL
    msg['To'] = EMAIL

    # Conexão segura
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.set_debuglevel(1)  # Mostra logs detalhados
        server.starttls()  # TLS obrigatório

        # Autenticação moderna
        server.login(EMAIL, PASSWORD.strip())

        # Envio
        server.send_message(msg)
        print("\n✅ Email enviado com sucesso!")

except smtplib.SMTPAuthenticationError:
    print("\n❌ Falha na autenticação. Verifique:")
    print("- Senha de aplicativo GERADA HOJE")
    print("- Verificação em duas etapas ATIVADA")
    print("- Servidor: smtp.office365.com")
    print("- Nenhum espaço na senha")
except Exception as e:
    print(f"\n⚠️ Erro inesperado: {e}")