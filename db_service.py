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

_REATRIBUICOES_CACHE = {"data": None, "timestamp": 0}

def obter_reatribuicoes_questoes() -> dict:
    """
    Retorna mapa de reatribuições de competência feitas pelo Master 1 (com cache de 60s):
    {
      "I.1.1": {
         "codigo_questao": "I.1.1",
         "remover_de": ["SUPLAV"],
         "adicionar_em": ["SIAE"]
      }
    }
    """
    global _REATRIBUICOES_CACHE
    import time
    agora = time.time()
    if _REATRIBUICOES_CACHE["data"] is not None and (agora - _REATRIBUICOES_CACHE["timestamp"] < 60):
        return _REATRIBUICOES_CACHE["data"]

    if not db:
        return {}
    try:
        docs = db.collection("reatribuicoes_questoes").stream()
        mapa = {}
        for d in docs:
            item = d.to_dict()
            cod = item.get("codigo_questao") or d.id
            mapa[cod] = item
        _REATRIBUICOES_CACHE["data"] = mapa
        _REATRIBUICOES_CACHE["timestamp"] = agora
        return mapa
    except Exception as e:
        print(f"Erro obter_reatribuicoes_questoes: {e}")
        return _REATRIBUICOES_CACHE["data"] or {}

def questao_pertence_subsecretaria(q: dict, sub_upper: str, reatrib_map: dict = None) -> bool:
    if sub_upper == "TODAS":
        return True
    cod = q.get("codigo", "")
    if reatrib_map and cod in reatrib_map:
        info_r = reatrib_map[cod]
        if sub_upper in [s.upper() for s in info_r.get("remover_de", [])]:
            return False
        if sub_upper in [s.upper() for s in info_r.get("adicionar_em", [])]:
            return True
    return bool(q.get("is_comum") or sub_upper in [s.upper() for s in q.get("subsecretarias", [])])

def filtrar_questoes_subsecretaria(subsecretaria: str) -> list:
    sub_upper = (subsecretaria or "TODAS").strip().upper()
    if sub_upper == "TODAS":
        return ALL_QUESTIONS_DATA
    reatrib_map = obter_reatribuicoes_questoes()
    filtradas = []
    for q in ALL_QUESTIONS_DATA:
        if questao_pertence_subsecretaria(q, sub_upper, reatrib_map):
            q_copy = dict(q)
            cod = q_copy.get("codigo", "")
            if cod in reatrib_map and sub_upper in [s.upper() for s in reatrib_map[cod].get("adicionar_em", [])]:
                subs_atuais = list(q_copy.get("subsecretarias", []))
                if sub_upper not in subs_atuais:
                    subs_atuais.append(sub_upper)
                q_copy["subsecretarias"] = subs_atuais
                q_copy["tipo_atribuicao"] = f"Redirecionada ({sub_upper})"
            filtradas.append(q_copy)
    return filtradas

def obter_total_questoes_subsecretaria(subsecretaria: str) -> int:
    sub_upper = (subsecretaria or "").strip().upper()
    if not sub_upper or sub_upper == "TODAS":
        return len(ALL_QUESTIONS_DATA)
    return len(filtrar_questoes_subsecretaria(sub_upper))

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
    - questoes_respondidas: questões aprovadas/no formulário espelhado do Ponto Focal
    - respostas_usuarios: questões enviadas agrupadas por servidor (email)
    """
    sub_upper = (subsecretaria or "GERAL").strip().upper()
    default_doc = {
        "subsecretaria": sub_upper,
        "status_consolidacao": "em_andamento",
        "questoes_respondidas": {},
        "respostas_usuarios": {}
    }
    if not db:
        return default_doc
    try:
        doc = db.collection("quadro_subsecretarias").document(sub_upper).get()
        d = doc.to_dict() if doc.exists else dict(default_doc)
        if "questoes_respondidas" not in d or not isinstance(d["questoes_respondidas"], dict):
            d["questoes_respondidas"] = {}
        if "respostas_usuarios" not in d or not isinstance(d["respostas_usuarios"], dict):
            d["respostas_usuarios"] = {}

        # Se não estiver consolidado oficialmente, hidrata automaticamente submissões individuais
        # que estavam apenas no histórico (submissoes_par) para dentro de respostas_usuarios
        if d.get("status_consolidacao") != "consolidado_oficial":
            ultima_limpeza = d.get("ultima_limpeza_homologacao", "")
            precisa_salvar = False
            try:
                subs_docs = db.collection("submissoes_par").where("responsavel.subsecretaria", "==", sub_upper).stream()
                subs_list = [s.to_dict() for s in subs_docs]
                subs_list.sort(key=lambda x: x.get("data_envio", ""))
                for s in subs_list:
                    if s.get("tipo_envio") not in ["resposta_individual", None]:
                        continue
                    dt_env = s.get("data_envio", "")
                    if ultima_limpeza and dt_env <= ultima_limpeza:
                        continue
                    resp_info = s.get("responsavel", {})
                    u_email = (resp_info.get("email") or "").strip().lower()
                    if not u_email:
                        continue
                    if u_email not in d["respostas_usuarios"]:
                        q_user_map = {}
                        for r in s.get("respostas", []):
                            cod = r.get("codigo_questao")
                            if not cod:
                                continue
                            no_quadro = d["questoes_respondidas"].get(cod, {})
                            email_no_quadro = (no_quadro.get("respondido_por", {}).get("email") or "").strip().lower()
                            st_inicial = no_quadro.get("status_validacao", "enviado") if email_no_quadro == u_email else "enviado"
                            q_user_map[cod] = {
                                "codigo_questao": cod,
                                "eixo": r.get("eixo", ""),
                                "tema": r.get("tema", ""),
                                "tipo_atribuicao": r.get("tipo_atribuicao", ""),
                                "enunciado": r.get("enunciado", ""),
                                "opcao_marcada": r.get("opcao_marcada"),
                                "evidencia_normativa": r.get("evidencia_normativa", ""),
                                "respondido_por": {
                                    "nome": resp_info.get("nome", "Servidor"),
                                    "email": u_email,
                                    "setor": resp_info.get("setor", "Não informado"),
                                    "subsecretaria": sub_upper
                                },
                                "data_resposta": dt_env,
                                "status_validacao": st_inicial,
                                "mensagem_devolucao": no_quadro.get("mensagem_devolucao", "") if email_no_quadro == u_email else "",
                                "observacao_devolucao": no_quadro.get("observacao_devolucao", "") if email_no_quadro == u_email else "",
                                "total_devolucoes": no_quadro.get("total_devolucoes", 0) if email_no_quadro == u_email else 0
                            }
                        if q_user_map:
                            d["respostas_usuarios"][u_email] = {
                                "usuario": {
                                    "nome": resp_info.get("nome", "Servidor"),
                                    "email": u_email,
                                    "setor": resp_info.get("setor", "Não informado"),
                                    "subsecretaria": sub_upper
                                },
                                "protocolo_id": s.get("protocolo_id", ""),
                                "ultima_submissao": dt_env,
                                "questoes": q_user_map
                            }
                            precisa_salvar = True
            except Exception as eh:
                print(f"Aviso hidratacao respostas_usuarios: {eh}")

            if precisa_salvar:
                try:
                    db.collection("quadro_subsecretarias").document(sub_upper).set(d)
                except Exception:
                    pass

        return d
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
    """Retorna lista de questoes que foram devolvidas especificamente para este usuario."""
    email_clean = email.strip().lower()
    quadro = obter_quadro_subsecretaria(subsecretaria)
    devolvidas_map = {}

    # 1. Verifica em respostas_usuarios[email_clean]
    resp_usuarios = quadro.get("respostas_usuarios", {})
    if email_clean in resp_usuarios:
        u_questoes = resp_usuarios[email_clean].get("questoes", {})
        for cod, info in u_questoes.items():
            if info.get("status_validacao") == "devolvido":
                devolvidas_map[cod] = info

    # 2. Fallback em questoes_respondidas
    q_resp = quadro.get("questoes_respondidas", {})
    for cod, info in q_resp.items():
        resp_email = (info.get("respondido_por", {}).get("email") or "").strip().lower()
        if resp_email == email_clean and info.get("status_validacao") == "devolvido":
            devolvidas_map[cod] = info

    return list(devolvidas_map.values())

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
                    d["solicitou_reabertura"] = quadro.get("solicitou_reabertura", False)
                    d["motivo_reabertura"] = quadro.get("motivo_reabertura", "")
                    return d
            return {
                "protocolo_id": proto or f"{subsecretaria.upper()}-OFICIAL",
                "data_envio": quadro.get("data_consolidacao"),
                "responsavel": quadro.get("consolidado_por", {"subsecretaria": subsecretaria.upper()}),
                "tipo_envio": "consolidacao_oficial",
                "solicitou_reabertura": quadro.get("solicitou_reabertura", False),
                "motivo_reabertura": quadro.get("motivo_reabertura", "")
            }

        docs = db.collection("submissoes_par")\
            .where("responsavel.subsecretaria", "==", subsecretaria.upper())\
            .where("tipo_envio", "==", "consolidacao_oficial")\
            .limit(1).stream()
        for d in docs:
            sub = d.to_dict()
            sub["id"] = d.id
            sub["solicitou_reabertura"] = quadro.get("solicitou_reabertura", False)
            sub["motivo_reabertura"] = quadro.get("motivo_reabertura", "")
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

    existente = check_user_submission(email_clean)
    # REGRA: Usuário comum NÃO pode editar livremente após enviar; só pode reenviar se houver devolução pelo Master 2
    if user_perfil == "usuario_comum" and existente:
        devolucoes_pendentes = obter_pendencias_devolucao_usuario(email_clean, subsecretaria)
        if len(devolucoes_pendentes) == 0:
            return {
                "sucesso": False,
                "mensagem": f"questionario ja enviado (Protocolo {existente.get('protocolo_id')} já registrado). A edição só é liberada caso o Ponto Focal devolva alguma questão para revisão."
            }

    # Se for Master 2 consolidando oficialmente:
    if user_perfil in ["master_2", "master_1"] and eh_envio_final_master2:
        if ja_consolidado:
            return {
                "sucesso": False,
                "mensagem": f"questionario ja enviado (Consolidação oficial da subsecretaria {subsecretaria} já foi homologada sob o protocolo {ja_consolidado.get('protocolo_id')})."
            }
        
        # REGRA OBRIGATÓRIA: O Master 2 só pode consolidar e enviar oficialmente se todas as questões estiverem aprovadas/respondidas no formulário
        total_esperado = obter_total_questoes_subsecretaria(subsecretaria)
        quadro_temp = obter_quadro_subsecretaria(subsecretaria)
        q_map_temp = dict(quadro_temp.get("questoes_respondidas", {}))
        for r in respostas_preenchidas:
            q_map_temp[r["codigo_questao"]] = r

        # Filtra apenas questões pertencentes atualmente à subsecretaria
        questoes_atuais_cods = {q.get("codigo") for q in filtrar_questoes_subsecretaria(subsecretaria)}
        respondidas_validas = [cod for cod in q_map_temp.keys() if cod in questoes_atuais_cods]
        total_respondidas_efetivas = len(respondidas_validas)

        if total_esperado > 0 and total_respondidas_efetivas < total_esperado:
            faltantes = total_esperado - total_respondidas_efetivas
            return {
                "sucesso": False,
                "mensagem": f"A Consolidação Oficial só pode ser enviada quando TODAS as questões da subsecretaria estiverem aprovadas/preenchidas no formulário. Total exigido: {total_esperado} questões. No formulário até o momento: {total_respondidas_efetivas}. Faltam {faltantes} questão(ões) para completar 100%."
            }

        # Verifica se há questões devolvidas aguardando retorno nos usuários
        devolvidas = []
        for u_data in quadro_temp.get("respostas_usuarios", {}).values():
            for q_u in u_data.get("questoes", {}).values():
                if q_u.get("status_validacao") == "devolvido":
                    devolvidas.append(q_u)
        if devolvidas:
            return {
                "sucesso": False,
                "mensagem": f"Não é possível consolidar oficialmente: existem {len(devolvidas)} questão(ões) devolvida(s) aguardando revisão e reenvio pelos servidores."
            }

        dados["tipo_envio"] = "consolidacao_oficial"
    elif user_perfil in ["master_2", "master_1"] and not eh_envio_final_master2:
        dados["tipo_envio"] = "edicao_ponto_focal"
    else:
        dados["tipo_envio"] = "resposta_individual"

    now_iso = datetime.now(timezone.utc).isoformat()
    if eh_envio_final_master2 and user_perfil in ["master_2", "master_1"]:
        sub_id = gerar_protocolo(subsecretaria)
    else:
        sub_id = dados.get("protocolo_id") or (existente.get("protocolo_id") if existente else None) or gerar_protocolo(subsecretaria)
    dados["protocolo_id"] = sub_id
    dados["data_envio"] = now_iso
    dados["respostas"] = respostas_preenchidas
    dados["metricas"]["total_respondido"] = len(respostas_preenchidas)

    quadro = obter_quadro_subsecretaria(subsecretaria)
    q_map = quadro.get("questoes_respondidas", {})
    resp_usuarios = quadro.get("respostas_usuarios", {})

    if user_perfil == "usuario_comum":
        # Registra as respostas na ficha individual do servidor em respostas_usuarios
        user_entry = resp_usuarios.get(email_clean, {
            "usuario": {
                "nome": nome_resp,
                "email": email_clean,
                "setor": setor_resp,
                "subsecretaria": subsecretaria
            },
            "protocolo_id": sub_id,
            "ultima_submissao": now_iso,
            "questoes": {}
        })
        user_entry["usuario"] = {
            "nome": nome_resp,
            "email": email_clean,
            "setor": setor_resp,
            "subsecretaria": subsecretaria
        }
        user_entry["protocolo_id"] = sub_id
        user_entry["ultima_submissao"] = now_iso
        u_questoes = user_entry.get("questoes", {})

        for r in respostas_preenchidas:
            cod = r["codigo_questao"]
            anterior_u = u_questoes.get(cod, {})
            devolucoes_count = anterior_u.get("total_devolucoes", 0)

            if anterior_u.get("status_validacao") == "devolvido":
                status_val = "retorno_para_ajuste"
            else:
                status_val = "enviado"

            autor_info = {
                "nome": nome_resp,
                "email": email_clean,
                "setor": setor_resp,
                "subsecretaria": subsecretaria
            }
            item_q = {
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
            u_questoes[cod] = item_q

            # Se esta questão no quadro principal pertencia a este usuário e estava como devolvida, atualiza lá também
            if cod in q_map:
                qm_email = (q_map[cod].get("respondido_por", {}).get("email") or "").strip().lower()
                if qm_email == email_clean and q_map[cod].get("status_validacao") == "devolvido":
                    q_map[cod] = dict(item_q)

        user_entry["questoes"] = u_questoes
        resp_usuarios[email_clean] = user_entry
        # Salva na submissão a lista consolidada de todas as questões enviadas por este usuário
        dados["respostas"] = list(u_questoes.values())
        dados["metricas"]["total_respondido"] = len(dados["respostas"])

    else:
        # Master 2 ou Master 1 salvando diretamente no Formulário / Espelhamento
        for r in respostas_preenchidas:
            cod = r["codigo_questao"]
            anterior = q_map.get(cod, {})
            devolucoes_count = anterior.get("total_devolucoes", 0)
            if anterior.get("respondido_por"):
                autor_info = dict(anterior.get("respondido_por"))
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
                "status_validacao": "validado",
                "mensagem_devolucao": "",
                "observacao_devolucao": "",
                "total_devolucoes": devolucoes_count
            }

    quadro["questoes_respondidas"] = q_map
    quadro["respostas_usuarios"] = resp_usuarios
    quadro["ultima_atualizacao"] = now_iso

    if eh_envio_final_master2 and user_perfil in ["master_2", "master_1"]:
        quadro["status_consolidacao"] = "consolidado_oficial"
        quadro["protocolo_consolidacao"] = sub_id
        quadro["data_consolidacao"] = now_iso
        quadro["solicitou_reabertura"] = False
        quadro["motivo_reabertura"] = ""
        quadro["consolidado_por"] = {
            "nome": nome_resp,
            "email": email_clean,
            "setor": setor_resp,
            "subsecretaria": subsecretaria
        }
        # Na consolidação oficial, o documento da submissão leva TODAS as questões consolidadas do quadro + backup de respostas_usuarios
        dados["respostas"] = list(q_map.values())
        dados["respostas_usuarios_backup"] = dict(resp_usuarios)
        dados["metricas"]["total_respondido"] = len(dados["respostas"])

        # Após enviar para homologação oficial, limpa os dados provisórios do quadro vivo
        quadro["questoes_respondidas"] = {}
        quadro["respostas_usuarios"] = {}
        quadro["ultima_limpeza_homologacao"] = now_iso

    if db:
        try:
            db.collection("quadro_subsecretarias").document(subsecretaria).set(quadro)
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

def aprovar_questao_ponto_focal(subsecretaria: str, codigo_questao: str, solicitante_email: str, email_usuario: str = "") -> dict:
    """
    Aprova a resposta enviada por um servidor (ou todas de um servidor se codigo_questao == 'TODAS')
    e a envia imediatamente para o Formulário & Edição Espelhada (questoes_respondidas).
    """
    sub_upper = subsecretaria.strip().upper()
    email_u = (email_usuario or "").strip().lower()
    quadro = obter_quadro_subsecretaria(sub_upper)
    q_map = quadro.get("questoes_respondidas", {})
    resp_usuarios = quadro.get("respostas_usuarios", {})
    now_iso = datetime.now(timezone.utc).isoformat()

    # Caso especial: aprovar todas as questões pendentes de um usuário de uma só vez
    if codigo_questao == "TODAS" and email_u and email_u in resp_usuarios:
        u_questoes = resp_usuarios[email_u].get("questoes", {})
        count = 0
        for cod, item in u_questoes.items():
            if item.get("status_validacao") in ["enviado", "retorno_para_ajuste", "validado"]:
                item["status_validacao"] = "validado"
                item["aprovado_em"] = now_iso
                item["aprovado_por"] = solicitante_email
                item["mensagem_devolucao"] = ""
                item["observacao_devolucao"] = ""
                u_questoes[cod] = item
                q_map[cod] = dict(item)
                count += 1
        resp_usuarios[email_u]["questoes"] = u_questoes
        quadro["questoes_respondidas"] = q_map
        quadro["respostas_usuarios"] = resp_usuarios
        if db:
            db.collection("quadro_subsecretarias").document(sub_upper).set(quadro)
        return {
            "sucesso": True,
            "mensagem": f"{count} questão(ões) de {resp_usuarios[email_u].get('usuario', {}).get('nome', email_u)} aprovada(s) e enviada(s) para o Formulário!"
        }

    item_alvo = None
    if email_u and email_u in resp_usuarios:
        u_questoes = resp_usuarios[email_u].get("questoes", {})
        if codigo_questao in u_questoes:
            item_alvo = u_questoes[codigo_questao]
            item_alvo["status_validacao"] = "validado"
            item_alvo["aprovado_em"] = now_iso
            item_alvo["aprovado_por"] = solicitante_email
            item_alvo["mensagem_devolucao"] = ""
            item_alvo["observacao_devolucao"] = ""
            u_questoes[codigo_questao] = item_alvo
            resp_usuarios[email_u]["questoes"] = u_questoes

    if not item_alvo and codigo_questao in q_map:
        item_alvo = q_map[codigo_questao]
        item_alvo["status_validacao"] = "validado"
        item_alvo["aprovado_em"] = now_iso
        item_alvo["aprovado_por"] = solicitante_email
        item_alvo["mensagem_devolucao"] = ""
        item_alvo["observacao_devolucao"] = ""

    if not item_alvo:
        return {"sucesso": False, "mensagem": "Questão não encontrada para aprovação."}

    # Envia para o formulário consolidado (questoes_respondidas)
    q_map[codigo_questao] = dict(item_alvo)
    quadro["questoes_respondidas"] = q_map
    quadro["respostas_usuarios"] = resp_usuarios

    if db:
        try:
            db.collection("quadro_subsecretarias").document(sub_upper).set(quadro)
        except Exception as e:
            return {"sucesso": False, "mensagem": str(e)}

    return {
        "sucesso": True,
        "mensagem": f"Questão {codigo_questao} aprovada e enviada para o Formulário de Consolidação!"
    }

def devolver_questao_para_usuario(subsecretaria: str, codigo_questao: str, observacao: str, solicitante_email: str, email_usuario: str = "") -> dict:
    """
    Marca uma questão específica de um servidor como 'devolvido' para que ele possa editar e reenviar.
    """
    sub_upper = subsecretaria.strip().upper()
    email_u = (email_usuario or "").strip().lower()
    quadro = obter_quadro_subsecretaria(sub_upper)
    q_map = quadro.get("questoes_respondidas", {})
    resp_usuarios = quadro.get("respostas_usuarios", {})
    now_iso = datetime.now(timezone.utc).isoformat()

    item_alvo = None
    autor_email = email_u

    if email_u and email_u in resp_usuarios:
        u_questoes = resp_usuarios[email_u].get("questoes", {})
        if codigo_questao in u_questoes:
            item_alvo = u_questoes[codigo_questao]
            item_alvo["status_validacao"] = "devolvido"
            item_alvo["mensagem_devolucao"] = "o ponto focal do PAR solicitou uma nova analise"
            item_alvo["observacao_devolucao"] = observacao or ""
            item_alvo["devolvido_em"] = now_iso
            item_alvo["devolvido_por"] = solicitante_email
            item_alvo["total_devolucoes"] = item_alvo.get("total_devolucoes", 0) + 1
            u_questoes[codigo_questao] = item_alvo
            resp_usuarios[email_u]["questoes"] = u_questoes

    if codigo_questao in q_map:
        qm_item = q_map[codigo_questao]
        qm_email = (qm_item.get("respondido_por", {}).get("email") or "").strip().lower()
        if not autor_email:
            autor_email = qm_email
        if not item_alvo or qm_email == autor_email:
            qm_item["status_validacao"] = "devolvido"
            qm_item["mensagem_devolucao"] = "o ponto focal do PAR solicitou uma nova analise"
            qm_item["observacao_devolucao"] = observacao or ""
            qm_item["devolvido_em"] = now_iso
            qm_item["devolvido_por"] = solicitante_email
            qm_item["total_devolucoes"] = item_alvo.get("total_devolucoes", qm_item.get("total_devolucoes", 0) + 1) if item_alvo else (qm_item.get("total_devolucoes", 0) + 1)
            # Remove do formulário aprovado enquanto estiver devolvida
            del q_map[codigo_questao]
            if not item_alvo:
                item_alvo = qm_item
                if autor_email:
                    if autor_email not in resp_usuarios:
                        resp_usuarios[autor_email] = {
                            "usuario": qm_item.get("respondido_por", {"email": autor_email, "subsecretaria": sub_upper}),
                            "ultima_submissao": now_iso,
                            "questoes": {}
                        }
                    resp_usuarios[autor_email]["questoes"][codigo_questao] = item_alvo

    if not item_alvo:
        return {"sucesso": False, "mensagem": "Esta questão não foi encontrada para devolução."}

    quadro["questoes_respondidas"] = q_map
    quadro["respostas_usuarios"] = resp_usuarios

    if db:
        try:
            db.collection("quadro_subsecretarias").document(sub_upper).set(quadro)
            if autor_email:
                db.collection("usuarios_perfis").document(autor_email).set({
                    "tem_devolucao_pendente": True
                }, merge=True)
        except Exception as e:
            return {"sucesso": False, "mensagem": str(e)}

    return {
        "sucesso": True,
        "mensagem": f"Questão {codigo_questao} devolvida com sucesso para {item_alvo.get('respondido_por', {}).get('nome', autor_email)}."
    }

def nao_utilizar_resposta_usuario(subsecretaria: str, codigo_questao: str, solicitante_email: str, email_usuario: str) -> dict:
    """
    Marca a resposta de um usuário específico como 'nao_utilizada' (ex: quando dois usuários responderam a mesma questão).
    """
    sub_upper = subsecretaria.strip().upper()
    email_u = (email_usuario or "").strip().lower()
    quadro = obter_quadro_subsecretaria(sub_upper)
    q_map = quadro.get("questoes_respondidas", {})
    resp_usuarios = quadro.get("respostas_usuarios", {})
    now_iso = datetime.now(timezone.utc).isoformat()

    if not email_u or email_u not in resp_usuarios:
        return {"sucesso": False, "mensagem": "Usuário não encontrado no monitoramento desta subsecretaria."}

    u_questoes = resp_usuarios[email_u].get("questoes", {})
    if codigo_questao not in u_questoes:
        return {"sucesso": False, "mensagem": "Questão não encontrada nas respostas deste usuário."}

    item = u_questoes[codigo_questao]
    item["status_validacao"] = "nao_utilizada"
    item["descartado_em"] = now_iso
    item["descartado_por"] = solicitante_email
    u_questoes[codigo_questao] = item
    resp_usuarios[email_u]["questoes"] = u_questoes

    # Se esta resposta estava no formulário ativo e pertencia a este mesmo usuário, retira do formulário
    if codigo_questao in q_map:
        qm_email = (q_map[codigo_questao].get("respondido_por", {}).get("email") or "").strip().lower()
        if qm_email == email_u:
            del q_map[codigo_questao]

    quadro["questoes_respondidas"] = q_map
    quadro["respostas_usuarios"] = resp_usuarios

    if db:
        try:
            db.collection("quadro_subsecretarias").document(sub_upper).set(quadro)
        except Exception as e:
            return {"sucesso": False, "mensagem": str(e)}

    return {
        "sucesso": True,
        "mensagem": f"Resposta da questão {codigo_questao} ({item.get('respondido_por', {}).get('nome', email_u)}) marcada como 'Não Utilizar'."
    }

def solicitar_reabertura_consolidacao(subsecretaria: str, motivo: str, solicitante_email: str) -> dict:
    """
    Permite ao Master 2 solicitar ao Master 1 (Admin Geral) a devolução/reabertura da Consolidação Oficial para edição.
    """
    sub_upper = subsecretaria.strip().upper()
    quadro = obter_quadro_subsecretaria(sub_upper)
    if quadro.get("status_consolidacao") != "consolidado_oficial":
        return {"sucesso": False, "mensagem": "Esta subsecretaria ainda não está com consolidação finalizada."}

    now_iso = datetime.now(timezone.utc).isoformat()
    quadro["solicitou_reabertura"] = True
    quadro["motivo_reabertura"] = motivo or "Solicitação de ajuste pelo Ponto Focal."
    quadro["data_solicitacao_reabertura"] = now_iso
    quadro["solicitante_reabertura"] = solicitante_email

    proto = quadro.get("protocolo_consolidacao")
    if db:
        try:
            db.collection("quadro_subsecretarias").document(sub_upper).set(quadro)
            if proto:
                db.collection("submissoes_par").document(proto).set({
                    "solicitou_reabertura": True,
                    "motivo_reabertura": quadro["motivo_reabertura"],
                    "data_solicitacao_reabertura": now_iso
                }, merge=True)
        except Exception as e:
            return {"sucesso": False, "mensagem": str(e)}

    return {
        "sucesso": True,
        "mensagem": "Solicitação enviada ao Administrador Geral (Master 1)! Assim que autorizada, o formulário será reaberto para edição."
    }

def reabrir_consolidacao_oficial(subsecretaria: str, solicitante_email: str) -> dict:
    """
    Permite ao Master 1 (Admin Geral) cancelar/devolver a Consolidação Oficial para o Ponto Focal (Master 2)
    fazer alterações, restaurando integralmente as respostas no formulário do Ponto Focal.
    """
    sub_upper = subsecretaria.strip().upper()
    quadro = obter_quadro_subsecretaria(sub_upper)
    consolidacao_doc = check_consolidacao_subsecretaria(sub_upper)

    if not consolidacao_doc and quadro.get("status_consolidacao") != "consolidado_oficial":
        return {"sucesso": False, "mensagem": f"Nenhuma consolidação oficial ativa encontrada para {sub_upper}."}

    proto_id = (consolidacao_doc.get("protocolo_id") or consolidacao_doc.get("id") or quadro.get("protocolo_consolidacao")) if consolidacao_doc else quadro.get("protocolo_consolidacao")

    # Restaura as questões da consolidação oficial de volta para questoes_respondidas e respostas_usuarios
    q_restauradas = {}
    resp_usuarios_restaurados = {}
    if consolidacao_doc:
        for r in consolidacao_doc.get("respostas", []):
            cod = r.get("codigo_questao")
            if cod:
                r_copy = dict(r)
                r_copy["status_validacao"] = "validado"
                q_restauradas[cod] = r_copy
        if isinstance(consolidacao_doc.get("respostas_usuarios_backup"), dict):
            resp_usuarios_restaurados = consolidacao_doc.get("respostas_usuarios_backup")

    if not resp_usuarios_restaurados and q_restauradas:
        # Reconstrói respostas_usuarios a partir das questões restauradas caso seja consolidação anterior
        for cod, r_item in q_restauradas.items():
            resp_por = r_item.get("respondido_por", {})
            u_email = (resp_por.get("email") or "").strip().lower() or "ponto_focal@seedf"
            if u_email not in resp_usuarios_restaurados:
                resp_usuarios_restaurados[u_email] = {
                    "usuario": {
                        "nome": resp_por.get("nome", "Ponto Focal"),
                        "email": u_email,
                        "setor": resp_por.get("setor", sub_upper),
                        "subsecretaria": sub_upper
                    },
                    "protocolo_id": proto_id or "",
                    "ultima_submissao": r_item.get("data_resposta", datetime.now(timezone.utc).isoformat()),
                    "questoes": {}
                }
            resp_usuarios_restaurados[u_email]["questoes"][cod] = dict(r_item)

    now_iso = datetime.now(timezone.utc).isoformat()
    quadro["status_consolidacao"] = "em_andamento"
    quadro["solicitou_reabertura"] = False
    quadro["motivo_reabertura"] = ""
    quadro["reaberto_em"] = now_iso
    quadro["reaberto_por"] = solicitante_email
    quadro["protocolo_consolidacao"] = None
    if q_restauradas:
        quadro["questoes_respondidas"] = q_restauradas
    if resp_usuarios_restaurados:
        quadro["respostas_usuarios"] = resp_usuarios_restaurados

    if db:
        try:
            db.collection("quadro_subsecretarias").document(sub_upper).set(quadro)
            # Atualiza quaisquer documentos consolidacao_oficial dessa subsecretaria em submissoes_par
            docs = db.collection("submissoes_par").where("responsavel.subsecretaria", "==", sub_upper).stream()
            for d in docs:
                sdata = d.to_dict()
                if sdata.get("tipo_envio") == "consolidacao_oficial":
                    db.collection("submissoes_par").document(d.id).set({
                        "tipo_envio": "consolidacao_reaberta_historico",
                        "reaberto_em": now_iso,
                        "reaberto_por": solicitante_email
                    }, merge=True)
        except Exception as e:
            return {"sucesso": False, "mensagem": str(e)}

    return {
        "sucesso": True,
        "mensagem": f"Consolidação da {sub_upper} devolvida com sucesso! Todas as {len(q_restauradas)} questões foram restauradas no painel do Ponto Focal para edição."
    }

def reatribuir_questao_reporte(reporte_id: str, nova_subsecretaria: str, resposta_master1: str = "") -> dict:
    """
    Redireciona uma questão reportada da Subsecretaria de origem para a Subsecretaria correta escolhida pelo Master 1.
    """
    if not db:
        return {"sucesso": False, "mensagem": "Banco de dados indisponível."}
    try:
        global _REATRIBUICOES_CACHE
        _REATRIBUICOES_CACHE["data"] = None
        rep_ref = db.collection("reportes_competencia").document(reporte_id)
        rep_doc = rep_ref.get()
        if not rep_doc.exists:
            return {"sucesso": False, "mensagem": "Reporte não encontrado."}

        rep = rep_doc.to_dict()
        cod = rep.get("codigo_questao", "")
        sub_origem = (rep.get("subsecretaria") or "").strip().upper()
        sub_destino = (nova_subsecretaria or "").strip().upper()

        if not cod or not sub_destino:
            return {"sucesso": False, "mensagem": "Código da questão e Subsecretaria de destino são obrigatórios."}

        now_iso = datetime.now(timezone.utc).isoformat()
        reatrib_ref = db.collection("reatribuicoes_questoes").document(cod)
        reatrib_doc = reatrib_ref.get()
        reatrib_data = reatrib_doc.to_dict() if reatrib_doc.exists else {
            "codigo_questao": cod,
            "remover_de": [],
            "adicionar_em": []
        }

        remover_de = set(s.upper() for s in reatrib_data.get("remover_de", []))
        adicionar_em = set(s.upper() for s in reatrib_data.get("adicionar_em", []))

        if sub_origem and sub_origem != sub_destino:
            remover_de.add(sub_origem)
            adicionar_em.discard(sub_origem)

        adicionar_em.add(sub_destino)
        remover_de.discard(sub_destino)

        reatrib_data["codigo_questao"] = cod
        reatrib_data["remover_de"] = list(remover_de)
        reatrib_data["adicionar_em"] = list(adicionar_em)
        reatrib_data["atualizado_em"] = now_iso
        reatrib_ref.set(reatrib_data)

        # Remove a questão do quadro ativo da subsecretaria de origem caso alguém já a tivesse rascunhado lá
        if sub_origem and sub_origem != sub_destino:
            quadro_orig = obter_quadro_subsecretaria(sub_origem)
            alterou_q = False
            if cod in quadro_orig.get("questoes_respondidas", {}):
                del quadro_orig["questoes_respondidas"][cod]
                alterou_q = True
            for u_em, u_obj in quadro_orig.get("respostas_usuarios", {}).items():
                if cod in u_obj.get("questoes", {}):
                    del u_obj["questoes"][cod]
                    alterou_q = True
            if alterou_q:
                db.collection("quadro_subsecretarias").document(sub_origem).set(quadro_orig)

        msg_padrao = resposta_master1 or f"Questão redirecionada da {sub_origem} para a {sub_destino} pelo Administrador Geral."
        rep_ref.set({
            "status": "reatribuido",
            "nova_subsecretaria": sub_destino,
            "resposta_master1": msg_padrao,
            "atualizado_em": now_iso
        }, merge=True)

        return {
            "sucesso": True,
            "mensagem": f"Questão {cod} retirada da {sub_origem} e encaminhada para o caderno da {sub_destino} com sucesso!"
        }
    except Exception as e:
        print(f"Erro reatribuir_questao_reporte: {e}")
        return {"sucesso": False, "mensagem": str(e)}

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
