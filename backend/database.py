# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Nome do arquivo do banco de dados (será criado automaticamente)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'simulados.db')}"

# Cria a conexão
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Cria a sessão (o canal de comunicação)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para criar os modelos
Base = declarative_base()