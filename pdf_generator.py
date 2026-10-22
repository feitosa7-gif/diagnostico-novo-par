# -*- coding: utf-8 -*-
import os
from collections import OrderedDict
from fpdf import FPDF

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

    respostas = dados_submissao.get("respostas", [])
    if not respostas:
        pdf.set_font("helvetica", "I", 9)
        pdf.cell(largura_util, 8, "Nenhuma resposta registrada para esta submissao.", ln=True)
        return bytes(pdf.output())

    # Agrupa respostas por respondente (Nome e Setor de quem respondeu cada pergunta)
    grupos = OrderedDict()
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
        if chave not in grupos:
            grupos[chave] = []
        grupos[chave].append(r)

    tem_multiplos_usuarios = len(grupos) > 1
    numero_global = 1

    for chave_usuario, itens_do_usuario in grupos.items():
        u_nome, u_setor, u_email = chave_usuario
        u_nome_limpo = limpar_unicode_latin1(u_nome)
        u_setor_limpo = limpar_unicode_latin1(u_setor)
        u_email_limpo = limpar_unicode_latin1(u_email)

        # Se houver múltiplos usuários respondentes, adiciona uma barra divisória de setor
        if tem_multiplos_usuarios:
            if pdf.get_y() > 220:
                pdf.add_page()
            else:
                pdf.ln(3)

            pdf.set_fill_color(225, 238, 252)
            pdf.set_draw_color(180, 205, 235)
            y_banner = pdf.get_y()
            pdf.rect(12, y_banner, largura_util, 7.5, style="DF")
            pdf.set_font("helvetica", "B", 8.5)
            pdf.set_text_color(19, 41, 75)
            pdf.set_xy(15, y_banner + 1.5)
            pdf.cell(largura_util - 6, 4.5, f"RESPOSTAS DO SETOR: {u_setor_limpo.upper()} | SERVIDOR: {u_nome_limpo.upper()}", ln=True)
            pdf.ln(2.5)

        # Renderiza todas as respostas daquele usuário
        for r in itens_do_usuario:
            cod = limpar_unicode_latin1(r.get("codigo_questao", ""))
            tema = limpar_unicode_latin1(r.get("tema", ""))
            enunciado = limpar_unicode_latin1(r.get("enunciado", ""))
            opcao = r.get("opcao_marcada")
            evidencia = limpar_unicode_latin1(r.get("evidencia_normativa", ""))

            if isinstance(opcao, list):
                opcao_str = limpar_unicode_latin1("; ".join(opcao)) if opcao else "(Sem resposta)"
            else:
                opcao_str = limpar_unicode_latin1(str(opcao)) if opcao else "(Sem resposta)"

            if pdf.get_y() > 245:
                pdf.add_page()

            pdf.set_x(12)
            pdf.set_font("helvetica", "B", 8.5)
            pdf.set_text_color(19, 41, 75)
            pdf.cell(largura_util, 4.5, f"{numero_global}. [{cod}] {tema}", ln=True)
            numero_global += 1

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

        # "no final dele, adicione o nome e o setor de quem respondeu aquela pergunta.
        # E se tiver mais de um como no formulario, pegue todas as respostas daquele usuario
        # e coloque o nome e setor embaixo, e va para o proximo repetindo esse processo na impressao."
        if pdf.get_y() > 240:
            pdf.add_page()
        else:
            pdf.ln(1.5)

        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(190, 205, 225)
        y_box = pdf.get_y()
        pdf.rect(12, y_box, largura_util, 20, style="DF")

        pdf.set_xy(16, y_box + 2)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(19, 41, 75)
        pdf.cell(largura_util - 8, 4, "RESPONSAVEL PELO PREENCHIMENTO DAS RESPOSTAS ACIMA:", ln=True)

        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(50, 50, 50)
        pdf.set_x(16)
        pdf.cell(90, 4, f"Servidor(a): {u_nome_limpo}", ln=False)
        pdf.cell(85, 4, f"Setor / Unidade: {u_setor_limpo}", ln=True)

        pdf.set_x(16)
        pdf.cell(90, 4, f"E-mail Institucional: {u_email_limpo or 'Nao informado'}", ln=False)
        pdf.cell(85, 4, f"Subsecretaria: {sub}", ln=True)

        pdf.set_y(y_box + 22)
        pdf.ln(3)

    return bytes(pdf.output())
