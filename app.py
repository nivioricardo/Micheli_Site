import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler
from typing import Union, List

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

from models import db, Orcamento

# Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Carrega o template
with open('templates/email_cliente.html', 'r', encoding='utf-8') as file:
    template_cliente = file.read()

# Carrega o template
with open('templates/email_admin.html', 'r', encoding='utf-8') as file:
    template_admin = file.read()

# Configuração do CSRF
csrf = CSRFProtect(app)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///orcamentos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '25101951')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Configuração de email atualizada para Gmail com autenticação segura
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
app.config['MAIL_TIMEOUT'] = 30

# Inicializa extensões
mail = Mail(app)
db.init_app(app)


# Configuração de logging melhorada
def configure_logging():
    if not os.path.exists('logs'):
        os.mkdir('logs')

    file_handler = RotatingFileHandler(
        'logs/orcamentos.log',
        maxBytes=10240,
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Aplicação de orçamentos iniciada')


configure_logging()

# Cria as tabelas do banco de dados
with app.app_context():
    db.create_all()


def enviar_email(destinatario: Union[str, List[str]], assunto: str, template: str, **kwargs) -> bool:
    """
    Função completa para envio de e-mails com template HTML

    Args:
        destinatario: E-mail ou lista de e-mails
        assunto: Assunto do e-mail
        template: Template HTML como string com {{var}} ou {var}
        **kwargs: Variáveis para substituição (ex: nome="João")

    Returns:
        bool: True se enviado com sucesso
    """
    try:
        # 1. Substitui variáveis no template (para {{var}} e {var})
        html = template
        for key, value in kwargs.items():
            html = html.replace(f'{{{{{key}}}}}', str(value))  # Para {{var}}
            html = html.replace(f'{{{key}}}', str(value))  # Para {var}

        # 2. Configurações do Gmail
        email_remetente = os.getenv("MAIL_GMAIL")
        email_password = os.getenv("MAIL_PASSWORD")

        if not email_remetente or not email_password:
            raise ValueError("Credenciais de e-mail não configuradas")

        # 3. Cria mensagem MIME
        msg = MIMEMultipart('alternative')
        msg['From'] = email_remetente
        msg['To'] = ', '.join([destinatario] if isinstance(destinatario, str) else destinatario)
        msg['Subject'] = assunto

        # 4. Adiciona partes (texto e HTML)
        part1 = MIMEText("Versão em texto simples para clientes que não suportam HTML", 'plain', 'utf-8')
        part2 = MIMEText(html, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)

        # 5. Envia usando SMTP (método que evita problema ASCII)
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_remetente, email_password)
            server.send_message(msg)  # Usando send_message em vez de sendmail

        return True

    except Exception as e:
        app.logger.error(f"Erro ao enviar e-mail: {str(e)}", exc_info=True)
        return False


@app.route('/')
def index():
    """Rota principal que renderiza o template HTML"""
    return render_template('index.html')


@app.route('/enviar_orcamento', methods=['POST'])
@csrf.exempt  # Remova em produção!
def enviar_orcamento():
    """Endpoint para processar o formulário de orçamento"""
    if request.method == 'POST':
        try:
            app.logger.info(f"Dados recebidos: {request.form}")

            # Validação dos campos obrigatórios
            campos_obrigatorios = {
                'nome': 'Nome completo',
                'email': 'Email',
                'telefone': 'Telefone',
                'rua': 'Rua',
                'numero': 'Número',
                'bairro': 'Bairro',
                'cidade': 'Cidade',
                'uf': 'UF',
                'cep': 'CEP',
                'produto': 'Produto',
                'quantidade': 'Quantidade',
                'estampa': 'Estampa'
            }

            faltantes = [
                nome_amigavel for campo, nome_amigavel in campos_obrigatorios.items()
                if campo not in request.form or not request.form[campo].strip()
            ]

            if faltantes:
                app.logger.warning(f"Campos obrigatórios faltando: {faltantes}")
                return jsonify({
                    'success': False,
                    'message': 'Preencha todos os campos obrigatórios: ' + ', '.join(faltantes)
                }), 400

            # Prepara os dados do orçamento
            dados_orcamento = {
                'nome': request.form['nome'].strip(),
                'email': request.form['email'].strip(),
                'telefone': request.form['telefone'].strip(),
                'rua': request.form['rua'].strip(),
                'numero': request.form['numero'].strip(),
                'complemento': request.form.get('complemento', '').strip(),
                'bairro': request.form['bairro'].strip(),
                'cidade': request.form['cidade'].strip(),
                'uf': request.form['uf'].strip().upper(),
                'cep': request.form['cep'].strip(),
                'produto': request.form['produto'].strip(),
                'tipo_produto': (request.form.get('tipo_caneca') or
                                 request.form.get('tipo_caderno', '')).strip(),
                'cor': request.form.get('cor_caneca', '').strip(),
                'quantidade_paginas': request.form.get('quantidade_de_paginas'),
                'quantidade': int(request.form['quantidade']),
                'estampa': request.form['estampa'].strip(),
                'observacoes': request.form.get('obs', '').strip(),
                'data_criacao': datetime.now(timezone.utc),
                'ip_cliente': request.remote_addr,
                'status': 'pendente'
            }

            # Cria e salva o orçamento
            novo_orcamento = Orcamento(**dados_orcamento)
            db.session.add(novo_orcamento)
            db.session.commit()

            email_cliente_ok = enviar_email(
                [dados_orcamento['email']],
                "Recebemos seu orçamento - Micheli Personalizados",
                template_cliente,
                **dados_orcamento
            )

            email_adm_ok = enviar_email(
                [os.getenv("MAIL_GMAIL"), dados_orcamento['email']],
                "Recebemos seu orçamento - Micheli Personalizados",
                template_admin,
                **dados_orcamento
            )

            if not all([email_adm_ok, email_cliente_ok]):
                app.logger.warning(f"Orçamento {novo_orcamento.id} salvo, mas emails falharam parcialmente")

            return jsonify({
                'success': True,
                'message': 'Orçamento enviado com sucesso!',
                'orcamento_id': novo_orcamento.id
            })

        except ValueError as e:
            db.session.rollback()
            app.logger.error(f"Erro de validação: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro ao processar orçamento: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Erro interno ao processar seu orçamento.'
            }), 500


@app.route('/test_smtp')
def test_smtp():
    """Rota para testar conexão SMTP"""
    try:
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.ehlo()
            if app.config['MAIL_USE_TLS']:
                server.starttls()
                server.ehlo()
            server.set_debuglevel(1)  # Ativa logs detalhados
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            return jsonify({
                'success': True,
                'message': 'Conexão SMTP bem-sucedida!'
            }), 200
    except smtplib.SMTPAuthenticationError as e:
        app.logger.error(f"Falha de autenticação SMTP: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Falha na autenticação SMTP. Verifique: '
                       '1. Se a senha de aplicativo está correta '
                       '2. Se a autenticação de dois fatores está ativada '
                       '3. Se o acesso de aplicativos menos seguros está ativado (não recomendado)'
        }), 401
    except Exception as e:
        app.logger.error(f"Erro SMTP: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Erro na conexão SMTP: {str(e)}"
        }), 500


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true')
