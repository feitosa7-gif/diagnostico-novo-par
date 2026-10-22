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
            raw_content = firebase_json_env.strip()
            if raw_content.startswith("{"):
                cred_dict = json.loads(raw_content)
            else:
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

ALL_QUESTIONS_DATA = []
if os.path.exists("questions_data.json"):
    try:
        with open("questions_data.json", "r", encoding="utf-8") as f:
            ALL_QUESTIONS_DATA = json.load(f)
    except Exception as e:
        print(f"Erro ao carregar questions_data.json em db_service: {e}")

def obter_total_questoes_subsecretaria(subsecretaria: str) -> int:
    sub_upper = subsecretaria.strip().upper()
    total = 0
    for q in ALL_QUESTIONS_DATA:
        if q.get("is_comum") or sub_upper in q.get("subsecretarias", []):
            total += 1
    return total

MASTER_1_EMAIL = "joao.carmo@nees.ufal.br".strip().lower()
MASTER_1_NAME = "jooa vitor feitosa do carmo"

def get_db():
    return db

def gerar_protocolo(subsecretaria: str) -> str:
    now_str = datetime.now().strftime("%Y%m%d")
    sufixo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{subsecretaria.upper()}-{now_str}-{sufixo}"

def get_or_create_user(nome: str, email: str, subsecretaria: str, setor: str = "") -> dict:
    email_clean = email.strip().lower()
    
    if email_clean == MASTER_1_EMAIL:
        user_data = {
            "nome": MASTER_1_NAME,
            "email": MASTER_1_EMAIL,
            "subsecretaria": "SE-DF",
            "setor": setor or "Coordenação Central",
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
        return {"nome": nome or "Servidor", "email": email_clean, "subsecretaria": subsecretaria, "setor": setor, "perfil": "usuario_comum", "status": "ativo"}

    try:
        user_ref = db.collection("usuarios_perfis").document(email_clean)
        doc = user_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            # Mantém estritamente o nome original da primeira inscrição
            if not data.get("nome") and nome:
                data["nome"] = nome.strip()
            # Atualiza subsecretaria e setor se fornecidos e ainda não definidos
            if subsecretaria and not data.get("subsecretaria"):
                data["subsecretaria"] = subsecretaria
            if setor and not data.get("setor"):
                data["setor"] = setor
            user_ref.set(data, merge=True)
            return data
        else:
            new_user = {
                "nome": (nome or "").strip() or "Servidor",
                "email": email_clean,
                "subsecretaria": subsecretaria,
                "setor": setor,
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
        return {"nome": nome or "Servidor", "email": email_clean, "subsecretaria": subsecretaria, "setor": setor, "perfil": "usuario_comum", "status": "ativo"}

def buscar_usuario_por_email(email: str) -> dict:
    email_clean = email.strip().lower()
    if not email_clean:
        return {}
    if email_clean == MASTER_1_EMAIL:
        return {
            "nome": MASTER_1_NAME,
            "email": MASTER_1_EMAIL,
            "subsecretaria": "SE-DF",
            "setor": "Coordenação Central",
            "perfil": "master_1",
            "status": "aprovado"
        }
    if not db:
        return {}
    try:
        doc = db.collection("usuarios_perfis").document(email_clean).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        print(f"Erro buscar_usuario_por_email: {e}")
    return {}

def obter_quadro_subsecretaria(subsecretaria: str) -> dict:
    """
    Retorna o documento consolidado vivo da Subsecretaria:
    {
      "subsecretaria": "SUBEB",
      "status_consolidacao": "em_andamento" | "consolidado_oficial",
      "protocolo_consolidacao": "...",
      "data_consolidacao": "...",
      "consolidado_por": {...},
      "questoes_respondidas": {
         "I.1.1": {
            "codigo_questao": "I.1.1",
            "opcao_marcada": [...],
            "evidencia_normativa": "...",
            "respondido_por": {"nome": "...", "email": "...", "setor": "..."},
            "data_resposta": "...",
            "status_validacao": "enviado" | "devolvido" | "validado",
            "mensagem_devolucao": "",
            "observacao_devolucao": ""
         }
      }
    }
    """
    sub_upper = (subsecretaria or "GERAL").strip().upper()
    default_doc = {
        "subsecretaria": sub_upper,
        "status_consolidacao": "em_andamento",
        "questoes_respondidas": {}
    }
    if not db:
        return default_doc
    try:
        doc = db.collection("quadro_subsecretarias").document(sub_upper).get()
        if doc.exists:
            d = doc.to_dict()
            if "questoes_respondidas" not in d:
                d["questoes_respondidas"] = {}
            return d
        return default_doc
    except Exception as e:
        print(f"Erro obter_quadro_subsecretaria: {e}")
        return default_doc

def listar_todos_quadros() -> list:
    if not db:
        return []
    try:
        docs = db.collection("quadro_subsecretarias").stream()
        return [d.to_dict() for d in docs]
    except Exception as e:
        print(f"Erro listar_todos_quadros: {e}")
        return []

def check_user_submission(email: str):
    email_clean = email.strip().lower()
    if not db:
        return None
    try:
        docs = db.collection("submissoes_par").where("responsavel.email", "==", email_clean).limit(20).stream()
        subs = []
        for d in docs:
            s = d.to_dict()
            s["id"] = d.id
            subs.append(s)
        if subs:
            # Retorna a mais recente
            subs.sort(key=lambda x: x.get("data_envio", ""), reverse=True)
            return subs[0]

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
                    "data_envio": udata.get("data_envio") or datetime.now(timezone.utc).isoformat(),
                    "responsavel": {
                        "nome": udata.get("nome"),
                        "email": email_clean,
                        "subsecretaria": udata.get("subsecretaria"),
                        "setor": udata.get("setor", "")
                    }
                }
    except Exception as e:
        print(f"Erro ao checar submissão: {e}")
    return None

def obter_pendencias_devolucao_usuario(email: str, subsecretaria: str) -> list:
    """Retorna lista de codigos de questoes que foram devolvidas para este usuario."""
    email_clean = email.strip().lower()
    quadro = obter_quadro_subsecretaria(subsecretaria)
    q_resp = quadro.get("questoes_respondidas", {})
    devolvidas = []
    for cod, info in q_resp.items():
        resp_email = (info.get("respondido_por", {}).get("email") or "").strip().lower()
        if resp_email == email_clean and info.get("status_validacao") == "devolvido":
            devolvidas.append(info)
    return devolvidas

def check_consolidacao_subsecretaria(subsecretaria: str):
    if not db or not subsecretaria:
        return None
    try:
        quadro = obter_quadro_subsecretaria(subsecretaria)
        if quadro.get("status_consolidacao") == "consolidado_oficial":
            proto = quadro.get("protocolo_consolidacao")
            if proto:
                sub_doc = db.collection("submissoes_par").document(proto).get()
                if sub_doc.exists:
                    d = sub_doc.to_dict()
                    d["id"] = sub_doc.id
                    return d
            return {
                "protocolo_id": proto or f"{subsecretaria.upper()}-OFICIAL",
                "data_envio": quadro.get("data_consolidacao"),
                "responsavel": quadro.get("consolidado_por", {"subsecretaria": subsecretaria.upper()}),
                "tipo_envio": "consolidacao_oficial"
            }

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
    """
    Salva as respostas enviadas pelo servidor comum (parciais do seu setor) ou pelo Ponto Focal (Master 2).
    """
    email_clean = dados["responsavel"]["email"].strip().lower()
    user_perfil = dados["responsavel"].get("perfil", "usuario_comum")
    subsecretaria = dados["responsavel"].get("subsecretaria", "GERAL").upper()
    nome_resp = dados["responsavel"].get("nome", "Servidor")
    setor_resp = dados["responsavel"].get("setor", "Não informado")
    eh_envio_final_master2 = dados.get("acao_master2") == "consolidar_oficial"

    respostas_enviadas = dados.get("respostas", [])
    # Filtra apenas questões que efetivamente possuem resposta preenchida
    respostas_preenchidas = []
    for r in respostas_enviadas:
        opc = r.get("opcao_marcada")
        if isinstance(opc, list) and len(opc) > 0:
            respostas_preenchidas.append(r)
        elif isinstance(opc, str) and opc.strip() != "":
            respostas_preenchidas.append(r)

    if len(respostas_preenchidas) == 0:
        return {
            "sucesso": False,
            "mensagem": "Selecione e responda pelo menos uma questão de competência do seu setor antes de enviar."
        }

    # Se a subsecretaria já foi consolidada oficialmente, não permite novas alterações por usuário comum
    ja_consolidado = check_consolidacao_subsecretaria(subsecretaria)
    if ja_consolidado and user_perfil == "usuario_comum":
        return {
            "sucesso": False, 
            "mensagem": f"questionario ja enviado (Consolidação oficial da subsecretaria {subsecretaria} já foi homologada sob o protocolo {ja_consolidado.get('protocolo_id')})."
        }

    # Se for Master 2 consolidando oficialmente:
    if user_perfil in ["master_2", "master_1"] and eh_envio_final_master2:
        if ja_consolidado:
            return {
                "sucesso": False,
                "mensagem": f"questionario ja enviado (Consolidação oficial da subsecretaria {subsecretaria} já foi homologada sob o protocolo {ja_consolidado.get('protocolo_id')})."
            }
        
        # REGRA OBRIGATÓRIA: O Master 2 só pode consolidar e enviar oficialmente se todas as questões forem enviadas pelos usuários
        total_esperado = obter_total_questoes_subsecretaria(subsecretaria)
        quadro_temp = obter_quadro_subsecretaria(subsecretaria)
        q_map_temp = dict(quadro_temp.get("questoes_respondidas", {}))
        for r in respostas_preenchidas:
            q_map_temp[r["codigo_questao"]] = r

        total_respondidas_efetivas = len(q_map_temp)
        if total_esperado > 0 and total_respondidas_efetivas < total_esperado:
            faltantes = total_esperado - total_respondidas_efetivas
            return {
                "sucesso": False,
                "mensagem": f"A Consolidação Oficial só pode ser enviada quando TODAS as questões da subsecretaria forem enviadas pelos setores. Total exigido: {total_esperado} questões. Respondidas até o momento: {total_respondidas_efetivas}. Faltam {faltantes} questão(ões) para completar 100%."
            }

        devolvidas = [r for r in q_map_temp.values() if r.get("status_validacao") == "devolvido"]
        if devolvidas:
            return {
                "sucesso": False,
                "mensagem": f"Não é possível consolidar oficialmente: existem {len(devolvidas)} questão(ões) devolvida(s) aguardando revisão e reenvio pelos setores."
            }

        dados["tipo_envio"] = "consolidacao_oficial"
    elif user_perfil in ["master_2", "master_1"] and not eh_envio_final_master2:
        dados["tipo_envio"] = "edicao_ponto_focal"
    else:
        dados["tipo_envio"] = "resposta_individual"

    existente = check_user_submission(email_clean)
    now_iso = datetime.now(timezone.utc).isoformat()
    # Se o usuário já possuía protocolo anterior ou enviou o protocolo no payload, reaproveita
    sub_id = dados.get("protocolo_id") or (existente.get("protocolo_id") if existente else None) or gerar_protocolo(subsecretaria)
    dados["protocolo_id"] = sub_id
    dados["data_envio"] = now_iso
    dados["respostas"] = respostas_preenchidas
    dados["metricas"]["total_respondido"] = len(respostas_preenchidas)

    # Atualiza o Quadro Coletivo da Subsecretaria
    quadro = obter_quadro_subsecretaria(subsecretaria)
    q_map = quadro.get("questoes_respondidas", {})

    for r in respostas_preenchidas:
        cod = r["codigo_questao"]
        anterior = q_map.get(cod, {})
        devolucoes_count = anterior.get("total_devolucoes", 0)
        
        # Se for reenvio de uma questão devolvida anteriormente pelo usuário comum:
        if user_perfil == "usuario_comum" and anterior.get("status_validacao") == "devolvido":
            status_val = "retorno_para_ajuste"
        elif user_perfil in ["master_2", "master_1"]:
            status_val = "validado"
        else:
            status_val = "enviado"
        
        # Se for Master 2 editando, preserva quem respondeu originalmente se já existir, ou assina como Ponto Focal
        if user_perfil in ["master_2", "master_1"] and anterior.get("respondido_por"):
            autor_info = anterior.get("respondido_por")
            autor_info["editado_pelo_ponto_focal"] = nome_resp
        else:
            autor_info = {
                "nome": nome_resp,
                "email": email_clean,
                "setor": setor_resp,
                "subsecretaria": subsecretaria
            }

        q_map[cod] = {
            "codigo_questao": cod,
            "eixo": r.get("eixo", ""),
            "tema": r.get("tema", ""),
            "tipo_atribuicao": r.get("tipo_atribuicao", ""),
            "enunciado": r.get("enunciado", ""),
            "opcao_marcada": r.get("opcao_marcada"),
            "evidencia_normativa": r.get("evidencia_normativa", ""),
            "respondido_por": autor_info,
            "data_resposta": now_iso,
            "status_validacao": status_val,
            "mensagem_devolucao": "",
            "observacao_devolucao": "",
            "total_devolucoes": devolucoes_count
        }

    quadro["questoes_respondidas"] = q_map
    quadro["ultima_atualizacao"] = now_iso

    if eh_envio_final_master2 and user_perfil in ["master_2", "master_1"]:
        quadro["status_consolidacao"] = "consolidado_oficial"
        quadro["protocolo_consolidacao"] = sub_id
        quadro["data_consolidacao"] = now_iso
        quadro["consolidado_por"] = {
            "nome": nome_resp,
            "email": email_clean,
            "setor": setor_resp,
            "subsecretaria": subsecretaria
        }
        # Na consolidação oficial, o documento da submissão leva TODAS as questões consolidadas do quadro
        dados["respostas"] = list(q_map.values())
        dados["metricas"]["total_respondido"] = len(dados["respostas"])

        # Após o envio para homologação/consolidação oficial, zera os registros provisórios do quadro vivo
        # para que fique limpo e zerado conforme solicitado
        quadro["questoes_respondidas"] = {}

    if db:
        try:
            db.collection("quadro_subsecretarias").document(subsecretaria).set(quadro, merge=True)
            db.collection("submissoes_par").document(sub_id).set(dados)
            db.collection("usuarios_perfis").document(email_clean).set({
                "ja_enviou": True,
                "submissao_protocolo": sub_id,
                "data_envio": now_iso,
                "tem_devolucao_pendente": False
            }, merge=True)
        except Exception as e:
            print(f"Erro ao gravar Firestore: {e}")
    
    os.makedirs("backup_respostas", exist_ok=True)
    with open(f"backup_respostas/{sub_id}.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    return {
        "sucesso": True,
        "protocolo_id": sub_id,
        "data_envio": now_iso,
        "tipo_envio": dados["tipo_envio"],
        "total_respondido": len(dados["respostas"]),
        "dados": dados
    }

def aprovar_questao_ponto_focal(subsecretaria: str, codigo_questao: str, solicitante_email: str) -> dict:
    """
    Permite ao Ponto Focal aprovar com um 'certinho' a resposta (seja retorno para ajuste ou enviada)
    marcando-a formalmente como validada/respondida.
    """
    sub_upper = subsecretaria.strip().upper()
    quadro = obter_quadro_subsecretaria(sub_upper)
    q_map = quadro.get("questoes_respondidas", {})

    if codigo_questao not in q_map:
        return {"sucesso": False, "mensagem": "Questão não encontrada no quadro."}

    item = q_map[codigo_questao]
    item["status_validacao"] = "validado"
    item["aprovado_em"] = datetime.now(timezone.utc).isoformat()
    item["aprovado_por"] = solicitante_email
    item["mensagem_devolucao"] = ""
    item["observacao_devolucao"] = ""

    q_map[codigo_questao] = item
    quadro["questoes_respondidas"] = q_map

    if db:
        try:
            db.collection("quadro_subsecretarias").document(sub_upper).set(quadro, merge=True)
        except Exception as e:
            return {"sucesso": False, "mensagem": str(e)}

    return {
        "sucesso": True,
        "mensagem": f"Questão {codigo_questao} validada e aprovada com sucesso!"
    }

def devolver_questao_para_usuario(subsecretaria: str, codigo_questao: str, observacao: str, solicitante_email: str) -> dict:
    """
    Marca uma questão específica no quadro da subsecretaria como 'devolvido' com a mensagem:
    'o ponto focal do PAR solicitou uma nova analise'
    e notifica o usuário que a respondeu para que ele possa editar e reenviar.
    """
    sub_upper = subsecretaria.strip().upper()
    quadro = obter_quadro_subsecretaria(sub_upper)
    q_map = quadro.get("questoes_respondidas", {})

    if codigo_questao not in q_map:
        return {"sucesso": False, "mensagem": "Esta questão ainda não foi respondida por nenhum servidor."}

    item = q_map[codigo_questao]
    autor_email = (item.get("respondido_por", {}).get("email") or "").strip().lower()

    item["status_validacao"] = "devolvido"
    item["mensagem_devolucao"] = "o ponto focal do PAR solicitou uma nova analise"
    item["observacao_devolucao"] = observacao or ""
    item["devolvido_em"] = datetime.now(timezone.utc).isoformat()
    item["devolvido_por"] = solicitante_email
    item["total_devolucoes"] = item.get("total_devolucoes", 0) + 1

    q_map[codigo_questao] = item
    quadro["questoes_respondidas"] = q_map

    if db:
        try:
            db.collection("quadro_subsecretarias").document(sub_upper).set(quadro, merge=True)
            if autor_email:
                db.collection("usuarios_perfis").document(autor_email).set({
                    "tem_devolucao_pendente": True
                }, merge=True)
        except Exception as e:
            return {"sucesso": False, "mensagem": str(e)}

    return {
        "sucesso": True,
        "mensagem": f"Questão {codigo_questao} devolvida com sucesso para {item.get('respondido_por', {}).get('nome', autor_email)}."
    }

def criar_reporte_competencia(subsecretaria: str, codigo_questao: str, enunciado: str, justificativa: str, reportado_por: dict) -> dict:
    """
    Registra um reporte do Ponto Focal (Master 2) informando ao Master 1 que determinada questão
    não é da competência de sua subsecretaria.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    reporte_id = f"REP-{subsecretaria.upper()}-{codigo_questao.replace('.', '_')}-{ ''.join(random.choices(string.digits, k=4)) }"
    doc_data = {
        "id": reporte_id,
        "subsecretaria": subsecretaria.upper(),
        "codigo_questao": codigo_questao,
        "enunciado": enunciado,
        "justificativa": justificativa,
        "reportado_por": reportado_por,
        "status": "pendente_analise",
        "data_reporte": now_iso
    }
    if db:
        try:
            db.collection("reportes_competencia").document(reporte_id).set(doc_data)
        except Exception as e:
            return {"sucesso": False, "mensagem": str(e)}
    return {"sucesso": True, "reporte": doc_data, "mensagem": "Reporte encaminhado diretamente ao Administrador Geral (Master 1)."}

def listar_reportes_competencia(subsecretaria: str = None) -> list:
    if not db:
        return []
    try:
        query = db.collection("reportes_competencia")
        if subsecretaria and subsecretaria != "TODAS":
            query = query.where("subsecretaria", "==", subsecretaria.upper())
        docs = query.stream()
        lista = [d.to_dict() for d in docs]
        lista.sort(key=lambda x: x.get("data_reporte", ""), reverse=True)
        return lista
    except Exception as e:
        print(f"Erro listar_reportes_competencia: {e}")
        return []

def atualizar_status_reporte(reporte_id: str, novo_status: str, resposta_master1: str = "") -> bool:
    if not db:
        return False
    try:
        db.collection("reportes_competencia").document(reporte_id).set({
            "status": novo_status,
            "resposta_master1": resposta_master1,
            "atualizado_em": datetime.now(timezone.utc).isoformat()
        }, merge=True)
        return True
    except Exception as e:
        print(f"Erro atualizar_status_reporte: {e}")
        return False

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

def solicitar_acesso_master2(email: str, nome: str, subsecretaria: str, setor: str = ""):
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

        dados_update = {
            "nome": nome,
            "email": email_clean,
            "subsecretaria": subsecretaria,
            "solicitou_master2": True,
            "status_solicitacao": "pendente",
            "data_solicitacao": datetime.now(timezone.utc).isoformat()
        }
        if setor:
            dados_update["setor"] = setor

        user_ref.set(dados_update, merge=True)
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
