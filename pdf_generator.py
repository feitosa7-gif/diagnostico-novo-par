# -*- coding: utf-8 -*-
import os
from fpdf import FPDF

def limpar_unicode_latin1(texto):
    if not texto:
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
    nome = limpar_unicode_latin1(resp.get("nome", "Servidor"))
    email = limpar_unicode_latin1(resp.get("email", "N/A"))
    sub = limpar_unicode_latin1(resp.get("subsecretaria", "N/A"))
    tipo_envio = limpar_unicode_latin1(dados_submissao.get("tipo_envio", "resposta_individual"))
    data_envio = limpar_unicode_latin1(dados_submissao.get("data_envio", ""))

    largura_util = 186

    # Caixa de identificação no topo
    pdf.set_fill_color(240, 245, 250)
    pdf.set_draw_color(180, 205, 235)
    pdf.rect(12, 30, largura_util, 24, style="DF")

    pdf.set_xy(16, 32)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(19, 41, 75)
    pdf.cell(largura_util - 8, 5, f"COMPROVANTE DE SUBMISSAO - PROTOCOLO: {proto}", ln=True)

    pdf.set_font("helvetica", "", 8.5)
    pdf.set_text_color(50, 50, 50)
    pdf.set_x(16)
    pdf.cell(90, 4.5, f"Responsavel: {nome}", ln=False)
    pdf.cell(90, 4.5, f"Subsecretaria: {sub}", ln=True)

    pdf.set_x(16)
    pdf.cell(90, 4.5, f"E-mail: {email}", ln=False)
    tipo_label = "Consolidacao Oficial Homologada" if tipo_envio == "consolidacao_oficial" else "Resposta de Servidor"
    pdf.cell(90, 4.5, f"Tipo: {tipo_label}", ln=True)

    pdf.set_x(16)
    pdf.cell(largura_util - 8, 4.5, f"Data do Registro: {data_envio[:19]}", ln=True)

    pdf.set_y(58)

    # Titulo da secao de questoes
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(19, 41, 75)
    pdf.cell(largura_util, 5, "DETALHAMENTO DAS RESPOSTAS E EVIDENCIAS", ln=True)
    pdf.set_draw_color(19, 41, 75)
    pdf.line(12, pdf.get_y(), 12 + largura_util, pdf.get_y())
    pdf.ln(3)

    respostas = dados_submissao.get("respostas", [])
    for idx, r in enumerate(respostas, 1):
        cod = limpar_unicode_latin1(r.get("codigo_questao", ""))
        tema = limpar_unicode_latin1(r.get("tema", ""))
        enunciado = limpar_unicode_latin1(r.get("enunciado", ""))
        opcao = r.get("opcao_marcada")
        evidencia = limpar_unicode_latin1(r.get("evidencia_normativa", ""))

        if isinstance(opcao, list):
            opcao_str = limpar_unicode_latin1("; ".join(opcao)) if opcao else "(Sem resposta)"
        else:
            opcao_str = limpar_unicode_latin1(str(opcao)) if opcao else "(Sem resposta)"

        # Verifica se cabe o bloco para evitar quebrar questão no rodapé
        if pdf.get_y() > 245:
            pdf.add_page()

        pdf.set_x(12)
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_text_color(19, 41, 75)
        pdf.cell(largura_util, 4.5, f"{idx}. [{cod}] {tema}", ln=True)

        pdf.set_x(12)
        pdf.set_font("helvetica", "", 8)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(largura_util, 4, enunciado)

        pdf.set_x(12)
        pdf.set_font("helvetica", "B", 8)
        pdf.set_text_color(0, 100, 50)
        # multi_cell em vez de cell fixa para quebrar linhas longas
        pdf.multi_cell(largura_util, 4, f"Resposta Selecionada: {opcao_str}")

        if evidencia:
            pdf.set_x(12)
            pdf.set_font("helvetica", "I", 7.5)
            pdf.set_text_color(120, 80, 0)
            pdf.multi_cell(largura_util, 3.5, f"Evidencia Normativa / Processo SEI: {evidencia}")

        pdf.set_draw_color(230, 230, 230)
        pdf.line(12, pdf.get_y() + 1.5, 12 + largura_util, pdf.get_y() + 1.5)
        pdf.ln(3)

    return bytes(pdf.output())
