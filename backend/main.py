# Em: backend/main.py

import os
import re
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# --- Imports para Auth ---
from typing import Optional, Annotated
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
# --- Fim dos Imports ---

from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine


# --- Configuração Inicial ---

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

print("--- INICIO DEBUG ---")
print(f"Arquivo .env encontrado? {os.path.exists('.env')}")
print(f"Chave lida: '{GEMINI_API_KEY}'")
print("--- FIM DEBUG ---")

if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY não encontrada no arquivo .env")

genai.configure(api_key=GEMINI_API_KEY)

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise EnvironmentError("SECRET_KEY não encontrada no arquivo .env")

# Inicializa o FastAPI App
app = FastAPI(
    title="API de Simulados",
    description="Gera questões de vestibular usando IA",
    version="1.0.0"
)

# --- CORS ---
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelos de Dados (Pydantic) ---

class SimuladoRequest(BaseModel):
    dificuldade: str
    materia: str
    numQuestoes: int

class Opcao(BaseModel):
    id: int
    texto: str

class QuestaoResponse(BaseModel):
    id: str
    vestibular: str
    materia: str
    dificuldade: str
    enunciado: str
    opcoes: list[Opcao]
    respostaCorreta: int 

# --- Modelos de Dados para Usuários ---

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

# Modelo para devolver uma Questão Salva
class QuestaoSalvaResponse(BaseModel):
    id: int
    enunciado: str
    opcoes: list[str]
    resposta_correta_idx: int
    
    class Config:
        from_attributes = True

# Modelo para devolver o Simulado Completo (Com as questões dentro)
class SimuladoCompleto(BaseModel):
    id: int
    vestibular: str
    materia: str
    dificuldade: str
    num_questoes: int
    data_criacao: datetime
    questoes: list[QuestaoSalvaResponse] # <--- A Lista de questões
    
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

# --- Configuração de Segurança (AuthN e AuthZ) ---

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
# Cria as tabelas no arquivo .db (se não existirem)
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Funções de Utilitário de Segurança ---

def verify_password(plain_password, hashed_password):
    """Verifica se a senha simples bate com a senha criptografada."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Gera o hash de uma senha."""
    return pwd_context.hash(password)

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db) # <--- Injetamos o banco
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # --- MUDANÇA AQUI: Usamos a SUA função 'get_user_by_username' ---
    user = get_user_by_username(db, username=token_data.username)
    # -----------------------------------------------------------------
    
    if user is None:
        raise credentials_exception
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria o Token JWT."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
# --- Função Auxiliar de Busca no Banco ---
def get_user_by_username(db: Session, username: str):
    """Busca um usuário no Banco de Dados SQL."""
    return db.query(models.User).filter(models.User.username == username).first()

# --- Dependência de Autorização Atualizada ---
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # Agora busca no banco de dados real
    user = get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


# --- Funções Auxiliares IA ---

def construir_prompt(vestibular_id: str, req: SimuladoRequest):
    return f"""
    Gere {req.numQuestoes} questões de múltipla escolha para um simulado de vestibular.
    Formato da Resposta: JSON
    
    Regras Estritas:
    1.  Vestibular: {vestibular_id.upper()}
    2.  Matéria: {req.materia}
    3.  Nível de Dificuldade: {req.dificuldade}
    4.  Cada questão DEVE ter 4 opções (A, B, C, D).
    5.  A resposta correta DEVE ser um número (0, 1, 2, ou 3).
    6.  O JSON de saída deve ser uma lista de objetos.
    7.  Não inclua "```json" ou "```" no início ou fim da resposta.
    8.  O ID da questão deve ser único (ex: 'q1', 'q2').
    
    Exemplo de formato JSON de saída:
    [
      {{
        "id": "q1",
        "enunciado": "Qual a capital da França?",
        "opcoes": [
          {{"id": 0, "texto": "Berlim"}},
          {{"id": 1, "texto": "Madri"}},
          {{"id": 2, "texto": "Paris"}},
          {{"id": 3, "texto": "Roma"}}
        ],
        "respostaCorreta": 2
      }}
    ]
    """

def limpar_json(texto_bruto):
    return re.sub(r'```json\s*|\s*```', '', texto_bruto.strip())


# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "API de Simulados está online!"}


# --- Endpoint de Registro (AGORA SALVA NO DB) ---
@app.post("/users/", response_model=UserResponse) 
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Registra um novo usuário no BANCO DE DADOS."""
    
    # 1. Verifica se já existe usando SUA função
    db_user = get_user_by_username(db, username=user.username)
    
    if db_user:
        raise HTTPException(status_code=400, detail="Usuário (username) já registrado")
    
    # 2. Criptografa a senha
    hashed_password = get_password_hash(user.password)
    
    # 3. Cria o objeto do Banco (models.User)
    new_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        role=user.role
    )
    
    # 4. Salva no SQLite
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


# --- Endpoint de Login (AGORA LÊ DO DB) ---
@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db) # <--- Injetamos o banco
):
    # --- MUDANÇA AQUI: Usamos a SUA função 'get_user_by_username' ---
    user = get_user_by_username(db, username=form_data.username)
    # ----------------------------------------------------------------
    
    # Verifica se existe e se a senha bate
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cria o token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


# --- O Endpoint Principal ---

@app.post("/gerar-simulado/{vestibular_id}", response_model=list[QuestaoResponse])
async def gerar_simulado(
    vestibular_id: str, 
    request_data: SimuladoRequest,
    current_user: models.User = Depends(get_current_user), # Recuperamos a segurança
    db: Session = Depends(get_db) 
):
    print("--- [DEBUG] 1. Rota chamada. Usuário autenticado. ---") 

    # Lógica de verificação de limite Premium (Opcional)
    if current_user.role == "free" and request_data.numQuestoes > 5:
        print("--- [DEBUG] Bloqueado: Limite Free excedido ---")
        raise HTTPException(status_code=403, detail="Limite de questões para conta Free excedido.")

    try:
        print(f"--- [DEBUG] 2. Iniciando IA para {vestibular_id}... ---")
        
        # 1. Configura a IA
        # (Certifique-se de que sua chave está configurada no genai.configure lá em cima)
        model = genai.GenerativeModel('gemini-2.5-flash') # Ou 'gemini-1.5-flash' / 'gemini-pro'
        
        # 2. Cria o Prompt
        prompt = construir_prompt(vestibular_id, request_data)
        
        print("--- [DEBUG] 3. Enviando prompt para o Google... (Pode demorar uns segundos) ---")
        
        # 3. CHAMA O GOOGLE (A parte que faltava!)
        response = model.generate_content(prompt)
        
        print("--- [DEBUG] 4. Resposta do Google recebida! ---")
        
        # 4. Limpa e converte o texto para JSON
        json_texto = limpar_json(response.text)
        questoes_json = json.loads(json_texto)
        
        print(f"--- [DEBUG] 5. JSON parseado com sucesso ({len(questoes_json)} questões). Salvando no BD... ---")
        
        # --- SALVANDO NO BANCO DE DADOS ---
        
        # 5. Cria o Cabeçalho do Simulado
        novo_simulado = models.SimuladoDB(
            vestibular=vestibular_id,
            materia=request_data.materia,
            dificuldade=request_data.dificuldade,
            num_questoes=request_data.numQuestoes,
            user_id=current_user.id  # Salva o ID do usuário logado
        )
        db.add(novo_simulado)
        db.commit()
        db.refresh(novo_simulado) # Pega o ID gerado (ex: 1, 2, 3...)

        print(f"--- [DEBUG] 6. Cabeçalho salvo (ID: {novo_simulado.id}). Salvando as questões... ---")

        # 6. Salva cada questão na tabela 'questoes_salvas'
        questoes_formatadas = []
        for q in questoes_json:
            # Prepara o objeto para devolver pro Front-end (QuestaoResponse)
            q['vestibular'] = vestibular_id.upper()
            q['materia'] = request_data.materia
            q['dificuldade'] = request_data.dificuldade
            questoes_formatadas.append(q)

            # Salva no Banco (QuestaoDB)
            # Nota: q['opcoes'] vem da IA como [{id:0, texto:"A"}, ...]. 
            # Aqui extraímos só o texto para salvar no banco.
            lista_opcoes_texto = [opt['texto'] for opt in q['opcoes']]

            nova_questao = models.QuestaoDB(
                simulado_id=novo_simulado.id, # Liga ao simulado pai
                enunciado=q['enunciado'],
                opcoes=lista_opcoes_texto, 
                resposta_correta_idx=q['respostaCorreta']
            )
            db.add(nova_questao)
        
        db.commit() # Confirma o salvamento das questões
        print("--- [DEBUG] 7. Tudo salvo! Retornando para o Front. ---")

        return questoes_formatadas

    except Exception as e:
        print(f"--- [ERRO FATAL NO BACKEND] : {e}")
        # Retorna o erro 500 para o front saber que falhou
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upgrade", response_model=Token)
async def upgrade_to_premium(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Simula a compra do plano Premium.
    Atualiza o usuário no banco e retorna um NOVO token com as permissões novas.
    """
    # 1. Atualiza no Banco
    current_user.role = "premium"
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    # 2. Gera um novo Token (agora com role="premium") para o frontend atualizar sem deslogar
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username, "role": "premium"},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/historico", response_model=list[SimuladoHistorico])
async def ler_historico(
    current_user: models.User = Depends(get_current_user), # Exige login
    db: Session = Depends(get_db)
):
    """
    Lista APENAS os simulados do usuário logado.
    """
    historico = db.query(models.SimuladoDB)\
        .filter(models.SimuladoDB.user_id == current_user.id)\
        .order_by(models.SimuladoDB.data_criacao.desc())\
        .all()
        
    return historico

@app.get("/simulados/{simulado_id}", response_model=SimuladoCompleto)
async def ler_simulado_detalhes(
    simulado_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Busca um simulado específico e suas questões.
    Verifica se o simulado pertence ao usuário logado.
    """
    simulado = db.query(models.SimuladoDB).filter(models.SimuladoDB.id == simulado_id).first()
    
    if not simulado:
        raise HTTPException(status_code=404, detail="Simulado não encontrado")
        
    if simulado.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para ver este simulado")
        
    return simulado