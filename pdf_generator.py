# -*- coding: utf-8 -*-
import os
from collections import OrderedDict
from fpdf import FPDF
import db_service

def limpar_unicode_latin1(texto):
    if texto is None:
        return ""
    s = str(texto)
    replacements = {
        "\u2022": "-", # bullet •
        "\u2013": "-", # en-dash –
        "\u2014": "-", # em-dash —
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
        "º": "o",
        "ª": "a",
        "§": "Art.",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")

class PARReportPDF(FPDF):
    def header(self):
        if os.path.exists("static/logo_par.jpg"):
            try:
                self.image("static/logo_par.jpg", 10, 8, 30)
            except Exception:
                pass
        self.set_font("helvetica", "B", 11)
        self.set_text_color(19, 41, 75)
        self.set_xy(42, 10)
        self.cell(0, 5, "SECRETARIA DE ESTADO DE EDUCACAO DO DISTRITO FEDERAL", ln=True, align="L")
        self.set_font("helvetica", "", 8.5)
        self.set_text_color(100, 100, 100)
        self.set_x(42)
        self.cell(0, 5, "SUPLAV / DPAPP - Diagnostico do Novo PAR (Ciclo 2026)", ln=True, align="L")
        self.set_draw_color(220, 220, 220)
        self.line(10, 26, 200, 26)
        self.set_y(30)

    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, f"Pagina {self.page_no()}/{{nb}} - Protocolo de Submissao SEEDF", align="C")

def gerar_pdf_submissao(dados_submissao: dict) -> bytes:
    # Margens: Esquerda 12mm, Direita 12mm -> Largura util = 210 - 24 = 186mm
    pdf = PARReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(12, 12, 12)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    resp = dados_submissao.get("responsavel", {})
    proto = limpar_unicode_latin1(dados_submissao.get("protocolo_id", "N/A"))
    nome_geral = limpar_unicode_latin1(resp.get("nome", "Servidor"))
    email_geral = limpar_unicode_latin1(resp.get("email", "N/A"))
    sub = limpar_unicode_latin1(resp.get("subsecretaria", "N/A"))
    setor_geral = limpar_unicode_latin1(resp.get("setor", "Nao informado"))
    tipo_envio = limpar_unicode_latin1(dados_submissao.get("tipo_envio", "resposta_individual"))
    data_envio = limpar_unicode_latin1(dados_submissao.get("data_envio", ""))

    largura_util = 186

    # Caixa de identificação no topo
    pdf.set_fill_color(240, 245, 250)
    pdf.set_draw_color(180, 205, 235)
    pdf.rect(12, 30, largura_util, 28, style="DF")

    pdf.set_xy(16, 32)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(19, 41, 75)
    pdf.cell(largura_util - 8, 5, f"COMPROVANTE DE SUBMISSAO - PROTOCOLO: {proto}", ln=True)

    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(50, 50, 50)
    pdf.set_x(16)
    pdf.cell(90, 4.5, f"Responsavel Geral / Emissor: {nome_geral}", ln=False)
    pdf.cell(90, 4.5, f"Subsecretaria: {sub}", ln=True)

    pdf.set_x(16)
    pdf.cell(90, 4.5, f"E-mail: {email_geral}", ln=False)
    pdf.cell(90, 4.5, f"Setor / Unidade: {setor_geral}", ln=True)

    pdf.set_x(16)
    if tipo_envio == "consolidacao_oficial":
        tipo_label = "Consolidacao Oficial Homologada"
    elif tipo_envio == "espelho_preliminar":
        tipo_label = "Espelho Preliminar da Subsecretaria"
    else:
        tipo_label = "Resposta Setorial de Servidor"

    pdf.cell(90, 4.5, f"Tipo: {tipo_label}", ln=False)
    pdf.cell(90, 4.5, f"Data do Registro: {data_envio[:19]}", ln=True)

    pdf.set_y(62)

    # Titulo da secao de questoes
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(19, 41, 75)
    pdf.cell(largura_util, 5, "DETALHAMENTO DAS RESPOSTAS E EVIDENCIAS", ln=True)
    pdf.set_draw_color(19, 41, 75)
    pdf.line(12, pdf.get_y(), 12 + largura_util, pdf.get_y())
    pdf.ln(3)

    respostas_raw = dados_submissao.get("respostas", [])
    if not respostas_raw:
        pdf.set_font("helvetica", "I", 9)
        pdf.cell(largura_util, 8, "Nenhuma resposta registrada para esta submissao.", ln=True)
        return bytes(pdf.output())

    # Ordena estritamente na ordem do questionário original (I.1.1 -> IV.8.2) e enriquece metadados
    respostas = db_service.ordenar_lista_respostas(respostas_raw)

    # Coleta os respondentes únicos mantendo a ordem em que aparecem
    respondentes_unicos = OrderedDict()
    for r in respostas:
        autor = r.get("respondido_por")
        if isinstance(autor, dict) and (autor.get("nome") or autor.get("setor")):
            nome_a = (autor.get("nome") or nome_geral).strip()
            setor_a = (autor.get("setor") or setor_geral).strip()
            email_a = (autor.get("email") or email_geral).strip()
        else:
            nome_a = nome_geral.strip()
            setor_a = setor_geral.strip()
            email_a = email_geral.strip()
        chave = (nome_a, setor_a, email_a)
        if chave not in respondentes_unicos:
            respondentes_unicos[chave] = 0
        respondentes_unicos[chave] += 1

    numero_global = 1
    eixo_atual = None

    # Renderiza todas as questões estritamente na ordem sequencial do questionário original
    for r in respostas:
        cod = limpar_unicode_latin1(r.get("codigo_questao", ""))
        eixo = limpar_unicode_latin1(r.get("eixo", ""))
        tema = limpar_unicode_latin1(r.get("tema", ""))
        enunciado = limpar_unicode_latin1(r.get("enunciado", ""))
        opcao = r.get("opcao_marcada")
        evidencia = limpar_unicode_latin1(r.get("evidencia_normativa", ""))

        autor = r.get("respondido_por")
        if isinstance(autor, dict) and (autor.get("nome") or autor.get("setor")):
            u_nome_limpo = limpar_unicode_latin1((autor.get("nome") or nome_geral).strip())
            u_setor_limpo = limpar_unicode_latin1((autor.get("setor") or setor_geral).strip())
        else:
            u_nome_limpo = nome_geral
            u_setor_limpo = setor_geral

        if isinstance(opcao, list):
            opcao_str = limpar_unicode_latin1("; ".join(opcao)) if opcao else "(Sem resposta)"
        else:
            opcao_str = limpar_unicode_latin1(str(opcao)) if opcao else "(Sem resposta)"

        # Barra de Eixo quando muda de Eixo
        if eixo and eixo != eixo_atual:
            eixo_atual = eixo
            if pdf.get_y() > 235:
                pdf.add_page()
            else:
                pdf.ln(2)
            pdf.set_fill_color(225, 238, 252)
            pdf.set_draw_color(180, 205, 235)
            y_banner = pdf.get_y()
            pdf.rect(12, y_banner, largura_util, 7, style="DF")
            pdf.set_font("helvetica", "B", 8.5)
            pdf.set_text_color(19, 41, 75)
            pdf.set_xy(15, y_banner + 1.3)
            pdf.cell(largura_util - 6, 4.5, f"EIXO {eixo.upper()}", ln=True)
            pdf.ln(2)

        if pdf.get_y() > 245:
            pdf.add_page()

        pdf.set_x(12)
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_text_color(19, 41, 75)
        pdf.cell(largura_util, 4.5, f"{numero_global}. [{cod}] {tema}", ln=True)
        numero_global += 1

        pdf.set_x(12)
        pdf.set_font("helvetica", "I", 7.5)
        pdf.set_text_color(90, 105, 125)
        pdf.cell(largura_util, 4, f"Respondido por: {u_nome_limpo} | Setor: {u_setor_limpo}", ln=True)

        pdf.set_x(12)
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(largura_util, 4, enunciado)

        pdf.set_x(12)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(0, 100, 50)
        pdf.multi_cell(largura_util, 4, f"Resposta Selecionada: {opcao_str}")

        if evidencia:
            pdf.set_x(12)
            pdf.set_font("helvetica", "I", 7.5)
            pdf.set_text_color(120, 80, 0)
            pdf.multi_cell(largura_util, 3.5, f"Evidencia Normativa / Processo SEI: {evidencia}")

        pdf.set_draw_color(230, 230, 230)
        pdf.line(12, pdf.get_y() + 1.5, 12 + largura_util, pdf.get_y() + 1.5)
        pdf.ln(2.5)

    # Quadro final de responsáveis pelo preenchimento
    if pdf.get_y() > 235:
        pdf.add_page()
    else:
        pdf.ln(2)

    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_text_color(19, 41, 75)
    pdf.cell(largura_util, 5, "QUADRO DE RESPONSAVEIS PELO PREENCHIMENTO:", ln=True)
    pdf.ln(1)

    for (u_nome, u_setor, u_email), qtd_q in respondentes_unicos.items():
        if pdf.get_y() > 250:
            pdf.add_page()
        u_nome_limpo = limpar_unicode_latin1(u_nome)
        u_setor_limpo = limpar_unicode_latin1(u_setor)
        u_email_limpo = limpar_unicode_latin1(u_email)

        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(190, 205, 225)
        y_box = pdf.get_y()
        pdf.rect(12, y_box, largura_util, 14, style="DF")

        pdf.set_xy(16, y_box + 2)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(19, 41, 75)
        pdf.cell(90, 4, f"Servidor(a): {u_nome_limpo}", ln=False)
        pdf.cell(85, 4, f"Setor / Unidade: {u_setor_limpo}", ln=True)

        pdf.set_font("helvetica", "", 7.5)
        pdf.set_text_color(60, 60, 60)
        pdf.set_x(16)
        pdf.cell(90, 4, f"E-mail: {u_email_limpo or 'Nao informado'}", ln=False)
        pdf.cell(85, 4, f"Subsecretaria: {sub} ({qtd_q} questao(oes))", ln=True)

        pdf.set_y(y_box + 16)

    return bytes(pdf.output())
