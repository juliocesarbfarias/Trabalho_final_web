# backend/main.py
import os
import re
import json
import google.generativeai as genai
from typing import Annotated, List
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from datetime import timedelta

# Importa nossos módulos organizados
import models, schemas, auth, crud
from database import engine

# --- Configuração ---
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY: raise EnvironmentError("GEMINI_API_KEY faltando.")
genai.configure(api_key=GEMINI_API_KEY)
# Cria as tabelas no banco automaticamente ao iniciar o app
models.Base.metadata.create_all(bind=engine) # Cria tabelas

app = FastAPI(title="API de Simulados", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Funções Auxiliares IA ---
def construir_prompt(vestibular_id: str, req: schemas.SimuladoRequest):
    return f"""
    Gere {req.numQuestoes} questões de múltipla escolha.
    Vestibular: {vestibular_id.upper()} | Matéria: {req.materia} | Dif: {req.dificuldade}
    Saída JSON estrito: lista de objetos com 'enunciado', 'opcoes' (lista de {{id, texto}}), 'respostaCorreta' (int).
    """

def limpar_json(text):
    return re.sub(r'```json\s*|\s*```', '', text.strip())

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "API Online e Refatorada!"}

@app.post("/users/", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    if auth.get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Usuário já existe")
    return crud.create_user(db, user)

@app.post("/token", response_model=schemas.Token)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(auth.get_db)):
    user = auth.get_user_by_username(db, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Dados incorretos")
    
    token = auth.create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}
# ENDPOINT : Exige 'current_user' (Login) para funcionar.
# ROTA PROTEGIDA COM INJEÇÃO DE DEPENDÊNCIA 
# 'db: Session = Depends(auth.get_db)' injeta a sessão do banco
# 'current_user' injeta a segurança.
@app.post("/gerar-simulado/{vestibular_id}")
def gerar_simulado(
    vestibular_id: str, 
    request_data: schemas.SimuladoRequest,
    # DEPENDÊNCIA: O FastAPI verifica o token antes de deixar entrar na função.
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db) 
):
    if current_user.role == "free" and request_data.numQuestoes > 5:
        raise HTTPException(status_code=403, detail="Limite Free excedido.")

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(construir_prompt(vestibular_id, request_data))
        questoes_json = json.loads(limpar_json(response.text))
        
        # Salva usando o módulo CRUD
        # Chama o CRUD para salvar no banco
        novo_simulado = crud.create_simulado(db, current_user.id, vestibular_id, request_data)
        
        questoes_formatadas = []
        for q in questoes_json:
            # Formata para retorno
            q['vestibular'] = vestibular_id.upper()
            q['materia'] = request_data.materia
            q['dificuldade'] = request_data.dificuldade
            questoes_formatadas.append(q)
            
            # Salva no banco
            crud.create_questao(db, novo_simulado.id, q, vestibular_id, request_data)
        
        db.commit() # Confirma tudo de uma vez
        return questoes_formatadas

    except Exception as e:
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar simulado.")

@app.get("/historico", response_model=List[schemas.SimuladoHistorico])
def ler_historico(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db)
):
    return crud.get_historico_by_user(db, current_user.id)

@app.get("/simulados/{simulado_id}", response_model=schemas.SimuladoCompleto)
def ler_detalhes(
    simulado_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db)
):
    simulado = crud.get_simulado_by_id(db, simulado_id)
    if not simulado or simulado.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Simulado não encontrado")
    return simulado

@app.post("/upgrade", response_model=schemas.Token)
def upgrade(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(auth.get_db)):
    current_user.role = "premium"
    db.add(current_user)
    db.commit()
    token = auth.create_access_token(data={"sub": current_user.username, "role": "premium"})
    return {"access_token": token, "token_type": "bearer"}