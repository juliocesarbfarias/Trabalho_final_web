# backend/schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Modelos de Simulados ---
class Opcao(BaseModel):
    id: int
    texto: str

class QuestaoResponse(BaseModel):
    id: str
    vestibular: str
    materia: str
    dificuldade: str
    enunciado: str
    opcoes: List[Opcao]
    respostaCorreta: int 

class SimuladoRequest(BaseModel):
    dificuldade: str
    materia: str
    numQuestoes: int

class QuestaoSalvaResponse(BaseModel):
    id: int
    enunciado: str
    opcoes: List[str]
    resposta_correta_idx: int
    class Config:
        from_attributes = True

class SimuladoCompleto(BaseModel):
    id: int
    vestibular: str
    materia: str
    dificuldade: str
    num_questoes: int
    data_criacao: datetime
    questoes: List[QuestaoSalvaResponse]
    class Config:
        from_attributes = True

class SimuladoHistorico(BaseModel):
    id: int
    vestibular: str
    materia: str
    dificuldade: str
    num_questoes: int
    data_criacao: datetime 
    class Config:
        from_attributes = True

# --- Modelos de Usuário ---
class UserBase(BaseModel):
    username: str
    role: str = "free"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None