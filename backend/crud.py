# backend/crud.py
from sqlalchemy.orm import Session
import models, schemas, auth

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_simulado(db: Session, user_id: int, vest: str, req: schemas.SimuladoRequest):
    db_simulado = models.SimuladoDB(
        vestibular=vest,
        materia=req.materia,
        dificuldade=req.dificuldade,
        num_questoes=req.numQuestoes,
        user_id=user_id
    )
    db.add(db_simulado)
    db.commit()
    db.refresh(db_simulado)
    return db_simulado

def create_questao(db: Session, simulado_id: int, questao_data: dict, vest: str, req: schemas.SimuladoRequest):
    # Converte opções para lista de strings
    opcoes_texto = [opt['texto'] for opt in questao_data['opcoes']]
    
    db_questao = models.QuestaoDB(
        simulado_id=simulado_id,
        enunciado=questao_data['enunciado'],
        opcoes=opcoes_texto,
        resposta_correta_idx=questao_data['respostaCorreta']
    )
    db.add(db_questao)
    return db_questao # Commit deve ser feito em lote pelo caller

def get_historico_by_user(db: Session, user_id: int):
    return db.query(models.SimuladoDB)\
        .filter(models.SimuladoDB.user_id == user_id)\
        .order_by(models.SimuladoDB.data_criacao.desc())\
        .all()

def get_simulado_by_id(db: Session, simulado_id: int):
    return db.query(models.SimuladoDB).filter(models.SimuladoDB.id == simulado_id).first()