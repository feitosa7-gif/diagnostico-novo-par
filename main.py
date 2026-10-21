import json
import os
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import db_service
import pdf_generator

app = FastAPI(title="Diagnóstico do Novo PAR - SEEDF")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

with open("questions_data.json", "r", encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)

class AuthLogin(BaseModel):
    nome: str
    email: str
    subsecretaria: Optional[str] = ""

class SolicitacaoMaster(BaseModel):
    nome: str
    email: str
    subsecretaria: str

class AlterarPerfil(BaseModel):
    email_alvo: str
    novo_perfil: str
    status_solicitacao: Optional[str] = "aprovado"

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.post("/api/auth/entrar")
def entrar(auth: AuthLogin):
    email_clean = auth.email.strip().lower()
    
    # Se for Master 1, não precisa de subsecretaria
    if email_clean == db_service.MASTER_1_EMAIL:
        user = db_service.get_or_create_user(auth.nome, auth.email, "SE-DF")
        return {
            "usuario": user,
            "ja_enviou": False,
            "submissao_anterior": None,
            "ja_consolidou_subsecretaria": False
        }

    user = db_service.get_or_create_user(auth.nome, auth.email, auth.subsecretaria)
    
    submissao_existente = db_service.check_user_submission(auth.email)
    
    # Checa também se a subsecretaria já foi consolidada por Administrador (Master 2)
    consolidacao_sub = None
    if user.get("subsecretaria"):
        consolidacao_sub = db_service.check_consolidacao_subsecretaria(user.get("subsecretaria"))

    return {
        "usuario": user,
        "ja_enviou": submissao_existente is not None,
        "submissao_anterior": submissao_existente,
        "ja_consolidou_subsecretaria": consolidacao_sub is not None,
        "consolidacao_oficial": consolidacao_sub
    }

@app.get("/api/questoes/{subsecretaria}")
def get_questoes(subsecretaria: str):
    sub_upper = subsecretaria.strip().upper()
    filtradas = []
    
    for q in ALL_QUESTIONS:
        if q["is_comum"] or sub_upper in q["subsecretarias"]:
            tipo_calc = "Comum – todas as áreas" if q["is_comum"] else "Específica da área"
            filtradas.append({
                "codigo": q["codigo"],
                "eixo": q["eixo"],
                "tema": q["tema"],
                "enunciado": q["enunciado"],
                "tipo_atribuicao": tipo_calc,
                "tipo_input": q["tipo_input"],
                "opcoes": q["opcoes"],
                "is_comum": q["is_comum"]
            })
            
    return {
        "subsecretaria": sub_upper,
        "total": len(filtradas),
        "questoes": filtradas
    }

@app.post("/api/submissoes/enviar")
def enviar_submissao(dados: dict = Body(...)):
    res = db_service.salvar_submissao(dados)
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.get("/api/submissoes/detalhes/{protocolo_id}")
def obter_detalhes_submissao(protocolo_id: str):
    sub = db_service.get_submissao_by_id(protocolo_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submissão não encontrada")
    return sub

@app.get("/api/submissoes/pdf/{protocolo_id}")
def baixar_pdf(protocolo_id: str):
    sub = db_service.get_submissao_by_id(protocolo_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submissão não encontrada")
    
    try:
        pdf_bytes = pdf_generator.gerar_pdf_submissao(sub)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="PAR_Submissao_{protocolo_id}.pdf"'
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")

@app.post("/api/usuarios/solicitar_master2")
def solicitar_master(solic: SolicitacaoMaster):
    res = db_service.solicitar_acesso_master2(solic.email, solic.nome, solic.subsecretaria)
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.get("/api/master/submissoes")
def listar_submissoes(solicitante_email: str, subsecretaria: Optional[str] = None):
    email_clean = solicitante_email.strip().lower()
    
    db = db_service.get_db()
    if not db:
        return {"submissoes": []}
        
    user_doc = db.collection("usuarios_perfis").document(email_clean).get()
    if not user_doc.exists:
        raise HTTPException(status_code=403, detail="Acesso não autorizado")
    
    user = user_doc.to_dict()
    perfil = user.get("perfil")
    
    if perfil not in ["master_1", "master_2"]:
        raise HTTPException(status_code=403, detail="Permissão negada.")
    
    query = db.collection("submissoes_par")
    
    if perfil == "master_2":
        user_sub = user.get("subsecretaria", "").upper()
        query = query.where("responsavel.subsecretaria", "==", user_sub)
    elif perfil == "master_1":
        if subsecretaria and subsecretaria != "TODAS":
            query = query.where("responsavel.subsecretaria", "==", subsecretaria.upper())
        
    docs = query.stream()
    lista = []
    for d in docs:
        item = d.to_dict()
        item["id"] = d.id
        lista.append(item)
        
    return {"perfil": perfil, "submissoes": lista}

@app.get("/api/master1/usuarios")
def gerenciar_usuarios(solicitante_email: str):
    email_clean = solicitante_email.strip().lower()
    if email_clean != db_service.MASTER_1_EMAIL:
        raise HTTPException(status_code=403, detail="Apenas o Administrador Central tem permissão para gerenciar perfis.")
    
    usuarios = db_service.listar_usuarios()
    return {"usuarios": usuarios}

@app.post("/api/master1/alterar_perfil")
def alterar_perfil(dados: AlterarPerfil, solicitante_email: str):
    email_clean = solicitante_email.strip().lower()
    if email_clean != db_service.MASTER_1_EMAIL:
        raise HTTPException(status_code=403, detail="Apenas o Administrador Central tem permissão para alterar perfis.")
    
    ok = db_service.alterar_perfil_usuario(dados.email_alvo, dados.novo_perfil, dados.status_solicitacao)
    return {"sucesso": ok}
