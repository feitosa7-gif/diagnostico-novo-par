import json
import os
from typing import List, Optional, Any
from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import db_service
import pdf_generator

app = FastAPI(title="Diagnóstico do Novo PAR - SEEDF")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "app": "Diagnostico Novo PAR - SEEDF"}

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

with open("questions_data.json", "r", encoding="utf-8") as f:
    ALL_QUESTIONS = json.load(f)

class AuthLogin(BaseModel):
    nome: Optional[str] = ""
    email: str
    subsecretaria: Optional[str] = ""
    setor: Optional[str] = ""

class SolicitacaoMaster(BaseModel):
    nome: str
    email: str
    subsecretaria: str
    setor: Optional[str] = ""

class AlterarPerfil(BaseModel):
    email_alvo: str
    novo_perfil: str
    status_solicitacao: Optional[str] = "aprovado"

class AprovarQuestaoPayload(BaseModel):
    subsecretaria: str
    codigo_questao: str
    solicitante_email: str
    email_usuario: Optional[str] = ""

class DevolverQuestaoPayload(BaseModel):
    subsecretaria: str
    codigo_questao: str
    observacao: Optional[str] = ""
    solicitante_email: str
    email_usuario: Optional[str] = ""

class NaoUtilizarQuestaoPayload(BaseModel):
    subsecretaria: str
    codigo_questao: str
    solicitante_email: str
    email_usuario: str

class AprovarMesclarPayload(BaseModel):
    subsecretaria: str
    codigo_questao: str
    solicitante_email: str

class SolicitarReaberturaPayload(BaseModel):
    subsecretaria: str
    motivo: Optional[str] = ""
    solicitante_email: str

class ReabrirConsolidacaoPayload(BaseModel):
    subsecretaria: str
    solicitante_email: str

class ReporteCompetenciaPayload(BaseModel):
    subsecretaria: str
    codigo_questao: str
    enunciado: str
    justificativa: str
    reportado_por: dict

class ResolverReportePayload(BaseModel):
    reporte_id: str
    novo_status: str
    resposta_master1: Optional[str] = ""
    solicitante_email: str

class ReatribuirReportePayload(BaseModel):
    reporte_id: str
    nova_subsecretaria: str
    resposta_master1: Optional[str] = ""
    solicitante_email: str

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.get("/api/auth/lookup")
def lookup_usuario(email: str):
    email_clean = email.strip().lower()
    if not email_clean:
        return {"encontrado": False}
    user = db_service.buscar_usuario_por_email(email_clean)
    if user and user.get("nome"):
        return {
            "encontrado": True,
            "nome": user.get("nome", ""),
            "subsecretaria": user.get("subsecretaria", ""),
            "setor": user.get("setor", ""),
            "perfil": user.get("perfil", "usuario_comum")
        }
    return {"encontrado": False}

@app.post("/api/auth/entrar")
def entrar(auth: AuthLogin):
    email_clean = auth.email.strip().lower()
    
    # Se for Master 1, não precisa de subsecretaria nem setor
    if email_clean == db_service.MASTER_1_EMAIL:
        user = db_service.get_or_create_user(auth.nome, auth.email, "SE-DF", "Coordenação Geral")
        return {
            "usuario": user,
            "ja_enviou": False,
            "submissao_anterior": None,
            "ja_consolidou_subsecretaria": False,
            "pendencias_devolucao": [],
            "quadro_subsecretaria": None
        }

    user = db_service.get_or_create_user(auth.nome, auth.email, auth.subsecretaria, auth.setor)
    sub_user = user.get("subsecretaria", auth.subsecretaria)
    
    submissao_existente = db_service.check_user_submission(auth.email)
    pendencias = db_service.obter_pendencias_devolucao_usuario(auth.email, sub_user) if sub_user else []
    quadro = db_service.obter_quadro_subsecretaria(sub_user) if sub_user else None
    
    # Checa também se a subsecretaria já foi consolidada por Administrador (Master 2)
    consolidacao_sub = None
    if sub_user:
        consolidacao_sub = db_service.check_consolidacao_subsecretaria(sub_user)

    return {
        "usuario": user,
        "ja_enviou": submissao_existente is not None,
        "submissao_anterior": submissao_existente,
        "ja_consolidou_subsecretaria": consolidacao_sub is not None,
        "consolidacao_oficial": consolidacao_sub,
        "pendencias_devolucao": pendencias,
        "quadro_subsecretaria": quadro
    }

@app.get("/api/questoes/{subsecretaria}")
def get_questoes(subsecretaria: str):
    sub_upper = subsecretaria.strip().upper()
    filtradas = []
    quadro = db_service.obter_quadro_subsecretaria(sub_upper)
    q_respondidas = quadro.get("questoes_respondidas", {})
    questoes_area = db_service.filtrar_questoes_subsecretaria(sub_upper)
    
    for q in questoes_area:
        tipo_calc = q.get("tipo_atribuicao") or ("Comum – todas as áreas" if q["is_comum"] else "Específica da área")
        cod = q["codigo"]
        estado_atual = q_respondidas.get(cod)
        filtradas.append({
            "codigo": cod,
            "eixo": q["eixo"],
            "tema": q["tema"],
            "enunciado": q["enunciado"],
            "tipo_atribuicao": tipo_calc,
            "tipo_input": q["tipo_input"],
            "opcoes": q["opcoes"],
            "is_comum": q["is_comum"],
            "tem_2025": q.get("tem_2025", False),
            "correspondencia_2025": q.get("correspondencia_2025", ""),
            "pergunta_2025": q.get("pergunta_2025", ""),
            "resposta_2025": q.get("resposta_2025", ""),
            "estado_coletivo": estado_atual
        })
            
    return {
        "subsecretaria": sub_upper,
        "total": len(filtradas),
        "questoes": filtradas,
        "quadro": quadro
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

@app.post("/api/espelho/pdf")
def baixar_pdf_espelho(dados: dict = Body(...)):
    try:
        pdf_bytes = pdf_generator.gerar_pdf_submissao(dados)
        sub_sigla = dados.get("responsavel", {}).get("subsecretaria", "ESPELHO")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="PAR_Espelho_{sub_sigla}.pdf"'
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF do espelho: {str(e)}")

@app.post("/api/usuarios/solicitar_master2")
def solicitar_master(solic: SolicitacaoMaster):
    res = db_service.solicitar_acesso_master2(solic.email, solic.nome, solic.subsecretaria, solic.setor)
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.post("/api/master2/aprovar_questao")
def aprovar_questao(payload: AprovarQuestaoPayload):
    res = db_service.aprovar_questao_ponto_focal(
        subsecretaria=payload.subsecretaria,
        codigo_questao=payload.codigo_questao,
        solicitante_email=payload.solicitante_email,
        email_usuario=payload.email_usuario or ""
    )
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.post("/api/master2/devolver_questao")
def devolver_questao(payload: DevolverQuestaoPayload):
    res = db_service.devolver_questao_para_usuario(
        subsecretaria=payload.subsecretaria,
        codigo_questao=payload.codigo_questao,
        observacao=payload.observacao or "",
        solicitante_email=payload.solicitante_email,
        email_usuario=payload.email_usuario or ""
    )
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.post("/api/master2/nao_utilizar_questao")
def nao_utilizar_questao(payload: NaoUtilizarQuestaoPayload):
    res = db_service.nao_utilizar_resposta_usuario(
        subsecretaria=payload.subsecretaria,
        codigo_questao=payload.codigo_questao,
        solicitante_email=payload.solicitante_email,
        email_usuario=payload.email_usuario
    )
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.post("/api/master2/aprovar_mesclar_questoes")
def aprovar_mesclar_questoes(payload: AprovarMesclarPayload):
    res = db_service.aprovar_mesclar_questoes_ponto_focal(
        subsecretaria=payload.subsecretaria,
        codigo_questao=payload.codigo_questao,
        solicitante_email=payload.solicitante_email
    )
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.post("/api/master2/solicitar_reabertura")
def solicitar_reabertura(payload: SolicitarReaberturaPayload):
    res = db_service.solicitar_reabertura_consolidacao(
        subsecretaria=payload.subsecretaria,
        motivo=payload.motivo or "",
        solicitante_email=payload.solicitante_email
    )
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.post("/api/master1/reabrir_consolidacao")
def reabrir_consolidacao(payload: ReabrirConsolidacaoPayload):
    email_clean = payload.solicitante_email.strip().lower()
    if email_clean != db_service.MASTER_1_EMAIL:
        raise HTTPException(status_code=403, detail="Apenas o Administrador Central tem permissão.")
    res = db_service.reabrir_consolidacao_oficial(
        subsecretaria=payload.subsecretaria,
        solicitante_email=payload.solicitante_email
    )
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.post("/api/master1/reatribuir_reporte")
def reatribuir_reporte(payload: ReatribuirReportePayload):
    email_clean = payload.solicitante_email.strip().lower()
    if email_clean != db_service.MASTER_1_EMAIL:
        raise HTTPException(status_code=403, detail="Apenas o Administrador Central tem permissão.")
    res = db_service.reatribuir_questao_reporte(
        reporte_id=payload.reporte_id,
        nova_subsecretaria=payload.nova_subsecretaria,
        resposta_master1=payload.resposta_master1 or ""
    )
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.post("/api/master2/reportar_competencia")
def reportar_competencia(payload: ReporteCompetenciaPayload):
    res = db_service.criar_reporte_competencia(
        subsecretaria=payload.subsecretaria,
        codigo_questao=payload.codigo_questao,
        enunciado=payload.enunciado,
        justificativa=payload.justificativa,
        reportado_por=payload.reportado_por
    )
    if not res.get("sucesso"):
        raise HTTPException(status_code=400, detail=res.get("mensagem"))
    return res

@app.get("/api/master/submissoes")
def listar_submissoes(solicitante_email: str, subsecretaria: Optional[str] = None):
    email_clean = solicitante_email.strip().lower()
    
    db = db_service.get_db()
    if not db:
        return {"submissoes": [], "quadro": None, "reportes": []}
        
    user_doc = db.collection("usuarios_perfis").document(email_clean).get()
    if not user_doc.exists:
        raise HTTPException(status_code=403, detail="Acesso não autorizado")
    
    user = user_doc.to_dict()
    perfil = user.get("perfil")
    
    if perfil not in ["master_1", "master_2"]:
        raise HTTPException(status_code=403, detail="Permissão negada.")
    
    query = db.collection("submissoes_par")
    quadro = None
    reportes = []
    
    if perfil == "master_2":
        user_sub = user.get("subsecretaria", "").upper()
        query = query.where("responsavel.subsecretaria", "==", user_sub)
        quadro = db_service.obter_quadro_subsecretaria(user_sub)
        reportes = db_service.listar_reportes_competencia(user_sub)
    elif perfil == "master_1":
        if subsecretaria and subsecretaria != "TODAS":
            query = query.where("responsavel.subsecretaria", "==", subsecretaria.upper())
            quadro = db_service.obter_quadro_subsecretaria(subsecretaria.upper())
        reportes = db_service.listar_reportes_competencia(subsecretaria)
        
    docs = query.stream()
    lista = []
    for d in docs:
        item = d.to_dict()
        item["id"] = d.id
        lista.append(item)
        
    lista.sort(key=lambda x: x.get("data_envio", ""), reverse=True)
    return {
        "perfil": perfil,
        "submissoes": lista,
        "quadro": quadro,
        "reportes": reportes
    }

@app.get("/api/master1/overview")
def master1_overview(solicitante_email: str):
    email_clean = solicitante_email.strip().lower()
    if email_clean != db_service.MASTER_1_EMAIL:
        raise HTTPException(status_code=403, detail="Apenas o Administrador Central tem permissão.")
    
    quadros = db_service.listar_todos_quadros()
    reportes = db_service.listar_reportes_competencia()
    usuarios = db_service.listar_usuarios()
    
    db = db_service.get_db()
    submissoes = []
    if db:
        for d in db.collection("submissoes_par").stream():
            item = d.to_dict()
            item["id"] = d.id
            submissoes.append(item)
    submissoes.sort(key=lambda x: x.get("data_envio", ""), reverse=True)
    
    return {
        "quadros": quadros,
        "reportes": reportes,
        "usuarios": usuarios,
        "submissoes": submissoes
    }

@app.post("/api/master1/resolver_reporte")
def resolver_reporte(payload: ResolverReportePayload):
    email_clean = payload.solicitante_email.strip().lower()
    if email_clean != db_service.MASTER_1_EMAIL:
        raise HTTPException(status_code=403, detail="Apenas o Administrador Central tem permissão.")
    ok = db_service.atualizar_status_reporte(payload.reporte_id, payload.novo_status, payload.resposta_master1 or "")
    return {"sucesso": ok}

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Iniciando servidor Diagnostico PAR na porta {port} (Host: {host})...")
    uvicorn.run("main:app", host=host, port=port, reload=False)
