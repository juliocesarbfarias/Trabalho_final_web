# backend/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, timedelta
from database import Base

def hora_brasil():
    return datetime.now(timezone(timedelta(hours=-3)))

# Tabela de Usuários
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="free")

    # Relacionamento: Um usuário tem vários simulados
    simulados = relationship("SimuladoDB", back_populates="dono")

# Tabela de Simulados (Cabeçalho)
class SimuladoDB(Base):
    __tablename__ = "historico_simulados"

    id = Column(Integer, primary_key=True, index=True)
    vestibular = Column(String, index=True)
    materia = Column(String)
    dificuldade = Column(String)
    num_questoes = Column(Integer)
    data_criacao = Column(DateTime, default=hora_brasil)

    # NOVO: Chave Estrangeira (Liga o simulado ao usuário que criou)
    user_id = Column(Integer, ForeignKey("users.id"))
    dono = relationship("User", back_populates="simulados")

    # NOVO: Relacionamento com as questões
    questoes = relationship("QuestaoDB", back_populates="simulado", cascade="all, delete-orphan")

# NOVA TABELA: Detalhes das Questões
class QuestaoDB(Base):
    __tablename__ = "questoes_salvas"

    id = Column(Integer, primary_key=True, index=True)
    
    # Liga a questão ao Simulado pai
    simulado_id = Column(Integer, ForeignKey("historico_simulados.id"))
    simulado = relationship("SimuladoDB", back_populates="questoes")

    enunciado = Column(String)
    # Vamos salvar as opções como JSON (lista de textos) para facilitar
    opcoes = Column(JSON) 
    resposta_correta_idx = Column(Integer)