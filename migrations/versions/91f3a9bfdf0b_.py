"""empty message

Revision ID: 91f3a9bfdf0b
Revises: 
Create Date: 2025-04-22 18:32:07.860711

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91f3a9bfdf0b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cliente',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=100), nullable=False),
    sa.Column('telefone', sa.String(length=20), nullable=False),
    sa.Column('email', sa.String(length=100), nullable=False),
    sa.Column('rua', sa.String(length=100), nullable=False),
    sa.Column('numero', sa.String(length=10), nullable=False),
    sa.Column('complemento', sa.String(length=50), nullable=True),
    sa.Column('bairro', sa.String(length=50), nullable=False),
    sa.Column('cep', sa.String(length=10), nullable=False),
    sa.Column('cidade', sa.String(length=50), nullable=False),
    sa.Column('uf', sa.String(length=2), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('orcamento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cliente_id', sa.Integer(), nullable=False),
    sa.Column('data', sa.DateTime(), nullable=True),
    sa.Column('produto', sa.String(length=20), nullable=False),
    sa.Column('tipo_produto', sa.String(length=20), nullable=True),
    sa.Column('cor', sa.String(length=20), nullable=True),
    sa.Column('quantidade_paginas', sa.Integer(), nullable=True),
    sa.Column('quantidade', sa.Integer(), nullable=False),
    sa.Column('estampa', sa.String(length=100), nullable=True),
    sa.Column('observacoes', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.ForeignKeyConstraint(['cliente_id'], ['cliente.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('orcamento')
    op.drop_table('cliente')
    # ### end Alembic commands ###
