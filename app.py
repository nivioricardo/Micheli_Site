from flask import Flask, render_template, request, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from models import db, Orcamento
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message

# Carrega variáveis de ambiente
load_dotenv()

app = Flask(__name__)

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
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'michelepersonalizados2025@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'michelepersonalizados2025@gmail.com')
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

def enviar_email(destinatario, assunto, template, **kwargs):
    """Função genérica para envio de emails"""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = assunto
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = destinatario

        if 'Reply-To' in kwargs:
            msg['Reply-To'] = kwargs['Reply-To']

        html = render_template(template, **kwargs)
        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.ehlo()
            if app.config['MAIL_USE_TLS']:
                server.starttls()
                server.ehlo()
            # Adicionado debug para verificar autenticação
            server.set_debuglevel(1)
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)

        app.logger.info(f"Email enviado para {destinatario}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        app.logger.error(f"Falha de autenticação SMTP ao enviar para {destinatario}. Verifique: "
                        f"1. Se a senha de aplicativo está correta "
                        f"2. Se a autenticação de dois fatores está ativada "
                        f"3. Se o acesso de aplicativos menos seguros está ativado (não recomendado). "
                        f"Erro detalhado: {str(e)}")
        return False
    except smtplib.SMTPException as e:
        app.logger.error(f"Erro SMTP ao enviar para {destinatario}: {str(e)}")
        return False
    except Exception as e:
        app.logger.error(f"Erro inesperado ao enviar email: {str(e)}", exc_info=True)
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

            # Envia os emails
            email_admin_ok = enviar_email(
                app.config['MAIL_DEFAULT_SENDER'],
                f"Novo Orçamento - {dados_orcamento['nome']}",
                'email_admin.html',
                **dados_orcamento
            )

            email_cliente_ok = enviar_email(
                dados_orcamento['email'],
                "Recebemos seu orçamento - Micheli Personalizados",
                'email_cliente.html',
                **dados_orcamento
            )

            if not all([email_admin_ok, email_cliente_ok]):
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