from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, func
from sqlalchemy.orm import validates
import re
from datetime import datetime, timezone
import phonenumbers
from email_validator import validate_email, EmailNotValidError
from flask import current_app

db = SQLAlchemy()


class Orcamento(db.Model):
    __tablename__ = 'orcamentos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    rua = db.Column(db.String(100), nullable=False)
    numero = db.Column(db.String(10), nullable=False)
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    cep = db.Column(db.String(10), nullable=False)
    produto = db.Column(db.String(50), nullable=False)
    tipo_produto = db.Column(db.String(50))
    cor = db.Column(db.String(50))
    quantidade_paginas = db.Column(db.Integer)
    quantidade = db.Column(db.Integer, nullable=False)
    estampa = db.Column(db.String(100), nullable=False)
    observacoes = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    ip_cliente = db.Column(db.String(45))
    status = db.Column(db.String(20), nullable=False, default='pendente')

    __table_args__ = (
        CheckConstraint('quantidade > 0', name='check_quantidade_positiva'),
        CheckConstraint(
            "uf IN ('AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO')",
            name='check_uf_valida'),
        CheckConstraint(
            "status IN ('pendente', 'processando', 'concluido', 'cancelado')",
            name='check_status_valido'),
        db.Index('idx_orcamento_email_produto', 'email', 'produto'),
    )

    @validates('email')
    def validate_email(self, key, email):
        current_app.logger.info(f"Validando e-mail: {email}")
        try:
            v = validate_email(email)
            current_app.logger.info(f"E-mail validado: {v.email}")
            return v.email
        except EmailNotValidError as e:
            current_app.logger.error(f"Email inválido: {email} - Erro: {str(e)}")
            raise ValueError("Por favor, insira um endereço de email válido")

    @validates('telefone')
    def validate_telefone(self, key, telefone):
        try:
            # Remove caracteres não numéricos
            telefone_limpo = re.sub(r'[^\d]', '', telefone)

            # Verifica se tem o número mínimo de dígitos (10 para fixo, 11 para celular)
            if len(telefone_limpo) not in [10, 11]:
                raise ValueError("Número de telefone deve ter 10 ou 11 dígitos")

            # Formata o telefone
            if len(telefone_limpo) == 10:
                return f"({telefone_limpo[:2]}) {telefone_limpo[2:6]}-{telefone_limpo[6:]}"
            else:
                return f"({telefone_limpo[:2]}) {telefone_limpo[2:7]}-{telefone_limpo[7:]}"

        except Exception as e:
            current_app.logger.error(f"Telefone inválido: {telefone} - Erro: {str(e)}")
            raise ValueError("Por favor, insira um número de telefone válido (XX) XXXX-XXXX ou (XX) XXXXX-XXXX")

    @validates('cep')
    def validate_cep(self, key, cep):
        try:
            # Remove caracteres não numéricos
            cep_limpo = re.sub(r'[^\d]', '', cep)

            if len(cep_limpo) != 8:
                raise ValueError("CEP deve conter 8 dígitos")

            return f"{cep_limpo[:5]}-{cep_limpo[5:]}"

        except Exception as e:
            current_app.logger.error(f"CEP inválido: {cep} - Erro: {str(e)}")
            raise ValueError("Por favor, insira um CEP válido no formato XXXXX-XXX")

    @validates('quantidade')
    def validate_quantidade(self, key, quantidade):
        try:
            qtd = int(quantidade)
            if qtd <= 0:
                raise ValueError("Quantidade deve ser maior que zero")
            return qtd
        except ValueError as e:
            current_app.logger.error(f"Quantidade inválida: {quantidade} - Erro: {str(e)}")
            raise ValueError("Por favor, insira uma quantidade válida (número inteiro positivo)")

    @validates('uf')
    def validate_uf(self, key, uf):
        ufs_validas = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT',
                       'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO',
                       'RR', 'SC', 'SP', 'SE', 'TO']
        if uf.upper() not in ufs_validas:
            current_app.logger.error(f"UF inválida: {uf}")
            raise ValueError("Por favor, selecione uma UF válida")
        return uf.upper()

    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'telefone': self.telefone,
            'endereco': {
                'rua': self.rua,
                'numero': self.numero,
                'complemento': self.complemento,
                'bairro': self.bairro,
                'cidade': self.cidade,
                'uf': self.uf,
                'cep': self.cep
            },
            'produto': self.produto,
            'tipo_produto': self.tipo_produto,
            'cor': self.cor,
            'quantidade_paginas': self.quantidade_paginas,
            'quantidade': self.quantidade,
            'estampa': self.estampa,
            'observacoes': self.observacoes,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'status': self.status
        }

    @classmethod
    def criar_apartir_dict(cls, data):
        """Cria uma instância de Orcamento a partir de um dicionário"""
        campos_validos = {k: v for k, v in data.items()
                          if k in cls.__table__.columns and not k.startswith('_')}
        return cls(**campos_validos)

    def __repr__(self):
        return (f'<Orcamento(id={self.id}, nome={self.nome}, produto={self.produto}, '
                f'quantidade={self.quantidade}, status={self.status})>')