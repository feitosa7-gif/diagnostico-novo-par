import json
import os
import random
import string
import base64
from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore

# Carregamento seguro e resiliente da credencial
cred_path = "firebase_credentials.json"
firebase_json_env = os.environ.get("FIREBASE_CREDENTIALS_JSON")

db = None

if firebase_json_env:
    try:
        firebase_admin.get_app()
    except ValueError:
        try:
            # Tenta decodificar se for base64 ou json puro
            raw_content = firebase_json_env.strip()
            if raw_content.startswith("{"):
                cred_dict = json.loads(raw_content)
            else:
                # Pode ter vindo codificado em base64
                decoded = base64.b64decode(raw_content).decode("utf-8")
                cred_dict = json.loads(decoded)
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Erro ao inicializar Firebase via variável de ambiente: {e}")
    try:
        db = firestore.client()
    except Exception as e:
        print(f"Erro ao obter client firestore: {e}")

elif os.path.exists(cred_path):
    try:
        firebase_admin.get_app()
    except ValueError:
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Erro ao inicializar Firebase via arquivo: {e}")
    try:
        db = firestore.client()
    except Exception as e:
        print(f"Erro ao obter client firestore: {e}")

MASTER_1_EMAIL = "joao.carmo@nees.ufal.br".strip().lower()
MASTER_1_NAME = "jooa vitor feitosa do carmo"

def get_db():
    return db

def gerar_protocolo(subsecretaria: str) -> str:
    now_str = datetime.now().strftime("%Y%m%d")
    sufixo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{subsecretaria.upper()}-{now_str}-{sufixo}"

def get_or_create_user(nome: str, email: str, subsecretaria: str) -> dict:
    email_clean = email.strip().lower()
    
    if email_clean == MASTER_1_EMAIL:
        user_data = {
            "nome": MASTER_1_NAME,
            "email": MASTER_1_EMAIL,
            "subsecretaria": "SE-DF",
            "perfil": "master_1",
            "status": "aprovado"
        }
        if db:
            try:
                db.collection("usuarios_perfis").document(email_clean).set(user_data, merge=True)
            except Exception as e:
                print(f"Aviso Firestore set master1: {e}")
        return user_data

    if not db:
        return {"nome": nome, "email": email_clean, "subsecretaria": subsecretaria, "perfil": "usuario_comum", "status": "ativo"}

    try:
        user_ref = db.collection("usuarios_perfis").document(email_clean)
        doc = user_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            data["nome"] = nome or data.get("nome", "")
            if subsecretaria:
                data["subsecretaria"] = subsecretaria
            user_ref.set(data, merge=True)
            return data
        else:
            new_user = {
                "nome": nome,
                "email": email_clean,
                "subsecretaria": subsecretaria,
                "perfil": "usuario_comum",
                "status": "ativo",
                "solicitou_master2": False,
                "ja_enviou": False,
                "criado_em": datetime.now(timezone.utc).isoformat()
            }
            user_ref.set(new_user)
            return new_user
    except Exception as e:
        print(f"Erro get_or_create_user: {e}")
        return {"nome": nome, "email": email_clean, "subsecretaria": subsecretaria, "perfil": "usuario_comum", "status": "ativo"}

def check_user_submission(email: str):
    email_clean = email.strip().lower()
    if not db:
        return None
    try:
        docs = db.collection("submissoes_par").where("responsavel.email", "==", email_clean).limit(1).stream()
        for d in docs:
            sub = d.to_dict()
            sub["id"] = d.id
            return sub
        
        user_doc = db.collection("usuarios_perfis").document(email_clean).get()
        if user_doc.exists:
            udata = user_doc.to_dict()
            if udata.get("ja_enviou"):
                proto = udata.get("submissao_protocolo")
                if proto:
                    p_doc = db.collection("submissoes_par").document(proto).get()
                    if p_doc.exists:
                        p_data = p_doc.to_dict()
                        p_data["id"] = p_doc.id
                        return p_data
                return {
                    "protocolo_id": proto or "REGISTRADO",
                    "id": proto or "REGISTRADO",
                    "data_envio": udata.get("data_envio") or udata.get("atualizado_em") or datetime.now(timezone.utc).isoformat(),
                    "responsavel": {
                        "nome": udata.get("nome"),
                        "email": email_clean,
                        "subsecretaria": udata.get("subsecretaria")
                    }
                }
    except Exception as e:
        print(f"Erro ao checar submissão: {e}")
    return None

def check_consolidacao_subsecretaria(subsecretaria: str):
    if not db or not subsecretaria:
        return None
    try:
        docs = db.collection("submissoes_par")\
            .where("responsavel.subsecretaria", "==", subsecretaria.upper())\
            .where("tipo_envio", "==", "consolidacao_oficial")\
            .limit(1).stream()
        for d in docs:
            sub = d.to_dict()
            sub["id"] = d.id
            return sub
    except Exception as e:
        print(f"Erro ao checar consolidação oficial: {e}")
    return None

def salvar_submissao(dados: dict) -> dict:
    email_clean = dados["responsavel"]["email"].strip().lower()
    user_perfil = dados["responsavel"].get("perfil", "usuario_comum")
    subsecretaria = dados["responsavel"].get("subsecretaria", "GERAL").upper()
    
    if user_perfil == "usuario_comum":
        existente = check_user_submission(email_clean)
        if existente:
            return {
                "sucesso": False, 
                "mensagem": "questionario ja enviado"
            }
            
    if user_perfil == "master_2":
        dados["tipo_envio"] = "consolidacao_oficial"
        ja_consolidado = check_consolidacao_subsecretaria(subsecretaria)
        if ja_consolidado and ja_consolidado.get("protocolo_id") != dados.get("protocolo_id"):
            return {
                "sucesso": False, 
                "mensagem": f"questionario ja enviado (Consolidação oficial da subsecretaria {subsecretaria} já foi homologada sob o protocolo {ja_consolidado.get('protocolo_id')})."
            }
    elif user_perfil == "master_1":
        dados["tipo_envio"] = "consolidacao_oficial"
    else:
        dados["tipo_envio"] = "resposta_individual"

    sub_id = dados.get("protocolo_id") or gerar_protocolo(subsecretaria)
    dados["protocolo_id"] = sub_id
    dados["data_envio"] = datetime.now(timezone.utc).isoformat()

    if db:
        try:
            db.collection("submissoes_par").document(sub_id).set(dados)
            db.collection("usuarios_perfis").document(email_clean).set({
                "ja_enviou": True,
                "submissao_protocolo": sub_id,
                "data_envio": dados["data_envio"]
            }, merge=True)
        except Exception as e:
            print(f"Erro ao gravar Firestore: {e}")
    
    os.makedirs("backup_respostas", exist_ok=True)
    with open(f"backup_respostas/{sub_id}.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    return {"sucesso": True, "protocolo_id": sub_id, "data_envio": dados["data_envio"], "dados": dados}

def get_submissao_by_id(protocolo_id: str):
    if db:
        try:
            doc = db.collection("submissoes_par").document(protocolo_id).get()
            if doc.exists:
                d = doc.to_dict()
                d["id"] = doc.id
                return d
        except Exception as e:
            print(f"Erro get_submissao_by_id Firestore: {e}")
    
    local_path = f"backup_respostas/{protocolo_id}.json"
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def solicitar_acesso_master2(email: str, nome: str, subsecretaria: str):
    email_clean = email.strip().lower()
    if not db:
        return {"sucesso": False, "mensagem": "Banco indisponível"}
    
    try:
        user_ref = db.collection("usuarios_perfis").document(email_clean)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            udata = user_doc.to_dict()
            if udata.get("solicitou_master2"):
                return {
                    "sucesso": False, 
                    "mensagem": "Você já enviou uma solicitação anteriormente. Ela está sendo avaliada pelo Administrador Central."
                }

        user_ref.set({
            "nome": nome,
            "email": email_clean,
            "subsecretaria": subsecretaria,
            "solicitou_master2": True,
            "status_solicitacao": "pendente",
            "data_solicitacao": datetime.now(timezone.utc).isoformat()
        }, merge=True)
        return {"sucesso": True, "mensagem": "Solicitação enviada com sucesso para homologação."}
    except Exception as e:
        return {"sucesso": False, "mensagem": str(e)}

def listar_usuarios():
    if not db:
        return []
    try:
        docs = db.collection("usuarios_perfis").stream()
        usuarios = []
        for d in docs:
            item = d.to_dict()
            usuarios.append(item)
        return usuarios
    except Exception as e:
        print(f"Erro listar_usuarios: {e}")
        return []

def alterar_perfil_usuario(email: str, novo_perfil: str, status_solicitacao: str = "aprovado"):
    email_clean = email.strip().lower()
    if not db:
        return False
    try:
        user_ref = db.collection("usuarios_perfis").document(email_clean)
        user_ref.set({
            "perfil": novo_perfil,
            "status_solicitacao": status_solicitacao,
            "atualizado_em": datetime.now(timezone.utc).isoformat()
        }, merge=True)
        return True
    except Exception as e:
        print(f"Erro alterar_perfil_usuario: {e}")
        return False
