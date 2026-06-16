# ==========================================================
# RECRUTADOR INTELIGENTE
# app.py
# PARTE 1/3
# ==========================================================

import streamlit as st
from groq import Groq

import json
import re
import tempfile
import pandas as pd

from pypdf import PdfReader
from docx import Document

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import getSampleStyleSheet

import plotly.express as px

# ==========================================================
# CONFIGURAÇÃO DA PÁGINA
# ==========================================================

st.set_page_config(
    page_title="Recrutador Inteligente",
    page_icon="🎯",
    layout="wide"
)

# ==========================================================
# SESSION STATE
# ==========================================================

DEFAULTS = {
    "phase": "config",
    "api_key": "",
    "job_description": "",
    "resume_text": "",
    "conversation": [],
    "current_question": "",
    "vfu_round": 0,
    "analysis_result": None,
    "final_result": None,
    "history": []
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==========================================================
# PROMPT PRINCIPAL
# ==========================================================

SYSTEM_PROMPT = """
Você é um Avaliador Técnico Especialista
em recrutamento baseado em evidências.

OBJETIVO:
Avaliar candidatos usando a metodologia
Evidence-to-Decision.

REGRAS:

1. Ignore jargões.
2. Ignore respostas genéricas.
3. Procure evidências concretas.
4. Valide experiências técnicas.
5. Detecte lacunas.
6. Gere no máximo 2 VFUs.

RETORNE SOMENTE JSON.

===========================
FORMATO VFU
===========================

{
    "status":"vfu",
    "round":1,
    "question":"Pergunta curta e objetiva"
}

===========================
FORMATO FINAL
===========================

{
    "status":"final",

    "classificacao":
    "Totalmente Alinhado",

    "recomendacao":
    "Avançar",

    "compatibilidade":85,

    "lacuna_principal":
    "...",

    "perfil_deficiencia":
    "...",

    "confianca":
    "Alto",

    "competencias":{
        "Python":90,
        "SQL":80,
        "Cloud":70,
        "Docker":75,
        "Comunicação":85
    },

    "evidencias":[
        "...",
        "..."
    ],

    "rationale":"..."
}

NUNCA RETORNE TEXTO FORA DO JSON.
"""

# ==========================================================
# UTILITÁRIOS
# ==========================================================

def create_client():

    return Groq(
        api_key=st.session_state.api_key
    )

# ==========================================================
# EXTRAIR JSON
# ==========================================================

def extract_json(text):

    try:
        return json.loads(text)

    except ValueError:

        depth = 0
        start = -1

        for i, char in enumerate(text):
            if char == "{":
                if start == -1:
                    start = i
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0 and start != -1:
                    try:
                        return json.loads(
                            text[start : i + 1]
                        )
                    except ValueError:
                        start = -1

        raise ValueError(
            "Resposta JSON inválida"
        )

# ==========================================================
# CHAMADA GROQ
# ==========================================================

def call_llm(messages):

    client = create_client()

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.2,
        max_completion_tokens=2500
    )

    return response.choices[0].message.content

# ==========================================================
# PDF
# ==========================================================

def extract_pdf(uploaded_file):

    reader = PdfReader(uploaded_file)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text

# ==========================================================
# DOCX
# ==========================================================

def extract_docx(uploaded_file):

    document = Document(uploaded_file)

    return "\n".join(
        p.text
        for p in document.paragraphs
    )

# ==========================================================
# CURRÍCULO
# ==========================================================

def extract_resume(uploaded_file):

    extension = uploaded_file.name.split(
        "."
    )[-1].lower()

    if extension == "pdf":
        return extract_pdf(uploaded_file)

    if extension == "docx":
        return extract_docx(uploaded_file)

    return uploaded_file.read().decode(
        "utf-8"
    )

# ==========================================================
# ANÁLISE INICIAL
# ==========================================================

def run_initial_analysis():

    prompt = f"""
Analise a vaga e o currículo.

DESCRIÇÃO DA VAGA:

{st.session_state.job_description}

CURRÍCULO:

{st.session_state.resume_text}

Retorne JSON:

{{
 "competencias_exigidas":[],
 "competencias_comprovadas":[],
 "lacunas":[]
}}
"""

    messages = [
        {
            "role":"system",
            "content":"""
Você é especialista em RH técnico.

Retorne apenas JSON.
"""
        },
        {
            "role":"user",
            "content":prompt
        }
    ]

    response = call_llm(messages)

    return extract_json(response)

# ==========================================================
# PRIMEIRA VFU
# ==========================================================

def start_evaluation():

    recruiter_prompt = f"""
Descrição da vaga:

{st.session_state.job_description}

Currículo:

{st.session_state.resume_text}

Analise o currículo.

Se houver dúvidas,
gere a primeira VFU.

Não finalize ainda.
"""

    messages = [
        {
            "role":"system",
            "content":SYSTEM_PROMPT
        },
        {
            "role":"user",
            "content":recruiter_prompt
        }
    ]

    response = call_llm(messages)

    result = extract_json(response)

    st.session_state.conversation = messages + [
        {
            "role": "assistant",
            "content": response
        }
    ]
    st.session_state.current_question = result
    st.session_state.vfu_round = 1

    return result

# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:

    st.title("⚙️ Configurações")

    st.session_state.api_key = st.text_input(
        "API Key Groq",
        type="password"
    )

    st.markdown("---")

    st.info(
        """
        Recrutador Inteligente

        Metodologia:
        Evidence-to-Decision

        Modelo:
        llama-3.3-70b-versatile
        """
    )

# ==========================================================
# TELA CONFIGURAÇÃO
# ==========================================================

if st.session_state.phase == "config":

    st.title("🎯 Recrutador Inteligente")

    st.subheader(
        "Descrição da Vaga"
    )

    st.session_state.job_description = (
        st.text_area(
            "Cole a descrição da vaga",
            height=250
        )
    )

    st.subheader(
        "Currículo"
    )

    uploaded_file = st.file_uploader(
        "Enviar PDF, DOCX ou TXT",
        type=[
            "pdf",
            "docx",
            "txt"
        ]
    )

    if uploaded_file:

        try:

            st.session_state.resume_text = (
                extract_resume(
                    uploaded_file
                )
            )

            st.success(
                "Currículo carregado"
            )

        except Exception as e:

            st.error(
                f"Erro: {e}"
            )

    st.session_state.resume_text = st.text_area(
        "Ou cole o currículo",
        value=st.session_state.resume_text,
        height=250
    )

    # ==========================================================
    # INICIAR AVALIAÇÃO
    # ==========================================================

    if st.button(
        "🚀 Iniciar Avaliação Baseada em Evidências",
        use_container_width=True
    ):

        if not st.session_state.api_key:

            st.error(
                "Informe sua API Key da Groq."
            )

            st.stop()

        if not st.session_state.job_description.strip():

            st.error(
                "Informe a descrição da vaga."
            )

            st.stop()

        if not st.session_state.resume_text.strip():

            st.error(
                "Informe o currículo."
            )

            st.stop()

        try:

            with st.spinner(
                "Analisando currículo..."
            ):

                analysis = run_initial_analysis()

                st.session_state.analysis_result = (
                    analysis
                )

                first_question = (
                    start_evaluation()
                )

                st.session_state.current_question = (
                    first_question
                )

                st.session_state.phase = (
                    "interaction"
                )

            st.rerun()

        except Exception as e:

            st.error(
                f"Erro durante a avaliação: {e}"
            )

# ==========================================================
# PROCESSAMENTO DAS RESPOSTAS
# ==========================================================

def process_candidate_answer(answer):

    st.session_state.conversation.append(
        {
            "role": "user",
            "content": answer
        }
    )

    control_prompt = f"""
Rodada atual:
{st.session_state.vfu_round}

Analise a resposta.

Decida:

1. Gerar nova VFU
OU

2. Encerrar avaliação.

Máximo permitido:
2 VFUs.
"""

    st.session_state.conversation.append(
        {
            "role":"system",
            "content":control_prompt
        }
    )

    response = call_llm(
        st.session_state.conversation
    )

    result = extract_json(response)

    st.session_state.conversation.append(
        {
            "role": "assistant",
            "content": response
        }
    )

    return result

# ==========================================================
# GERAR RELATÓRIO FORÇADO
# ==========================================================

def force_final_report():

    st.session_state.conversation.append(
        {
            "role":"user",
            "content":"""
Regra de parada atingida.

Gere agora o relatório final.

Retorne APENAS JSON FINAL.
"""
        }
    )

    response = call_llm(
        st.session_state.conversation
    )

    result = extract_json(response)

    st.session_state.conversation.append(
        {
            "role": "assistant",
            "content": response
        }
    )

    return result

# ==========================================================
# TELA DE INTERAÇÃO
# ==========================================================

if st.session_state.phase == "interaction":

    st.title(
        "🧠 Entrevista Baseada em Evidências"
    )

    if st.session_state.analysis_result:

        with st.expander(
            "📊 Análise Inicial"
        ):

            col1, col2 = st.columns(2)

            with col1:

                st.success(
                    "Competências comprovadas"
                )

                for item in st.session_state.analysis_result.get(
                    "competencias_comprovadas",
                    []
                ):
                    st.write(
                        f"✅ {item}"
                    )

            with col2:

                st.warning(
                    "Lacunas identificadas"
                )

                for item in st.session_state.analysis_result.get(
                    "lacunas",
                    []
                ):
                    st.write(
                        f"⚠️ {item}"
                    )

    st.markdown("---")

    st.info(
        f"Rodada VFU: "
        f"{st.session_state.vfu_round}/2"
    )

    question_data = (
        st.session_state.current_question
    )

    question = question_data.get(
        "question",
        "Pergunta indisponível."
    )

    with st.container(border=True):

        st.subheader(
            "Pergunta de Verificação"
        )

        st.write(question)

    answer = st.text_area(
        "Resposta do candidato",
        height=220
    )

    submit = st.button(
        "Enviar Resposta",
        use_container_width=True
    )

    if submit:

        if not answer.strip():

            st.warning(
                "Digite uma resposta."
            )

            st.stop()

        try:

            with st.spinner(
                "Validando evidências..."
            ):

                result = (
                    process_candidate_answer(
                        answer
                    )
                )

                # ==================
                # CASO FINAL
                # ==================

                if (
                    result.get("status")
                    == "final"
                ):

                    st.session_state.final_result = (
                        result
                    )

                    st.session_state.history.append(
                        {
                            "Classificação":
                            result.get(
                                "classificacao"
                            ),

                            "Compatibilidade":
                            result.get(
                                "compatibilidade"
                            ),

                            "Recomendação":
                            result.get(
                                "recomendacao"
                            )
                        }
                    )

                    st.session_state.phase = (
                        "report"
                    )

                    st.rerun()

                # ==================
                # NOVA VFU
                # ==================

                elif (
                    result.get("status")
                    == "vfu"
                ):

                    if (
                        st.session_state.vfu_round
                        >= 2
                    ):

                        final_report = (
                            force_final_report()
                        )

                        st.session_state.final_result = (
                            final_report
                        )

                        st.session_state.history.append(
                            {
                                "Classificação":
                                final_report.get(
                                    "classificacao"
                                ),

                                "Compatibilidade":
                                final_report.get(
                                    "compatibilidade"
                                ),

                                "Recomendação":
                                final_report.get(
                                    "recomendacao"
                                )
                            }
                        )

                        st.session_state.phase = (
                            "report"
                        )

                    else:

                        st.session_state.vfu_round += 1

                        st.session_state.current_question = (
                            result
                        )

                    st.rerun()

                # ==================
                # SEGURANÇA
                # ==================

                else:

                    final_report = (
                        force_final_report()
                    )

                    st.session_state.final_result = (
                        final_report
                    )

                    st.session_state.phase = (
                        "report"
                    )

                    st.rerun()

        except Exception as e:

            st.error(
                f"Erro ao processar resposta: {e}"
            )

# ==========================================================
# PDF
# ==========================================================

def generate_pdf(result):

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    )

    doc = SimpleDocTemplate(
        temp_file.name
    )

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "Relatório de Avaliação",
            styles["Title"]
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    elements.append(
        Paragraph(
            f"""
            <b>Classificação:</b>
            {result.get('classificacao')}
            """,
            styles["BodyText"]
        )
    )

    elements.append(
        Paragraph(
            f"""
            <b>Recomendação:</b>
            {result.get('recomendacao')}
            """,
            styles["BodyText"]
        )
    )

    elements.append(
        Paragraph(
            f"""
            <b>Compatibilidade:</b>
            {result.get('compatibilidade')}%
            """,
            styles["BodyText"]
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    elements.append(
        Paragraph(
            "<b>Justificativa</b>",
            styles["Heading2"]
        )
    )

    elements.append(
        Paragraph(
            result.get(
                "rationale",
                ""
            ),
            styles["BodyText"]
        )
    )

    doc.build(elements)

    return temp_file.name

# ==========================================================
# RELATÓRIO FINAL
# ==========================================================

if st.session_state.phase == "report":

    result = st.session_state.final_result

    st.title(
        "📊 Relatório Final"
    )

    # ======================================================
    # DASHBOARD
    # ======================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Compatibilidade",
            f"{result.get('compatibilidade',0)}%"
        )

    with col2:

        st.metric(
            "Confiança",
            result.get(
                "confianca",
                "-"
            )
        )

    with col3:

        st.metric(
            "Classificação",
            result.get(
                "classificacao",
                "-"
            )
        )

    with col4:

        st.metric(
            "Recomendação",
            result.get(
                "recomendacao",
                "-"
            )
        )

    st.progress(
        float(
            result.get(
                "compatibilidade",
                0
            )
        ) / 100
    )

    st.markdown("---")

    # ======================================================
    # RESUMO
    # ======================================================

    col_a, col_b = st.columns(2)

    with col_a:

        st.subheader(
            "Principal Lacuna"
        )

        st.warning(
            result.get(
                "lacuna_principal",
                "-"
            )
        )

    with col_b:

        st.subheader(
            "Perfil de Deficiência"
        )

        st.info(
            result.get(
                "perfil_deficiencia",
                "-"
            )
        )

    st.markdown("---")

    # ======================================================
    # COMPETÊNCIAS
    # ======================================================

    st.subheader(
        "Radar de Competências"
    )

    skills = result.get(
        "competencias",
        {}
    )

    if skills:

        df = pd.DataFrame(
            {
                "Competência":
                list(skills.keys()),

                "Nota":
                list(skills.values())
            }
        )

        fig = px.line_polar(
            df,
            r="Nota",
            theta="Competência",
            line_close=True
        )

        fig.update_layout(
            height=600
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.markdown("---")

    # ======================================================
    # EVIDÊNCIAS
    # ======================================================

    st.subheader(
        "Evidências Detectadas"
    )

    evidencias = result.get(
        "evidencias",
        []
    )

    if evidencias:

        for evidence in evidencias:

            st.success(
                evidence
            )

    st.markdown("---")

    # ======================================================
    # JUSTIFICATIVA
    # ======================================================

    st.subheader(
        "Justificativa Analítica"
    )

    st.write(
        result.get(
            "rationale",
            "Não informado."
        )
    )

    st.markdown("---")

    # ======================================================
    # EXPORTAÇÃO PDF
    # ======================================================

    try:

        pdf_path = generate_pdf(
            result
        )

        with open(
            pdf_path,
            "rb"
        ) as pdf_file:

            st.download_button(
                label="📄 Baixar Relatório PDF",
                data=pdf_file,
                file_name="relatorio_avaliacao.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    except Exception as e:

        st.error(
            f"Erro ao gerar PDF: {e}"
        )

    st.markdown("---")

    # ======================================================
    # HISTÓRICO
    # ======================================================

    st.subheader(
        "Histórico da Sessão"
    )

    if st.session_state.history:

        history_df = pd.DataFrame(
            st.session_state.history
        )

        st.dataframe(
            history_df,
            use_container_width=True
        )

    else:

        st.info(
            "Nenhuma avaliação anterior."
        )

    st.markdown("---")

    # ======================================================
    # NOVA AVALIAÇÃO
    # ======================================================

    if st.button(
        "🔄 Nova Avaliação",
        use_container_width=True
    ):

        st.session_state.phase = (
            "config"
        )

        st.session_state.job_description = ""

        st.session_state.resume_text = ""

        st.session_state.conversation = []

        st.session_state.current_question = ""

        st.session_state.vfu_round = 0

        st.session_state.analysis_result = None

        st.session_state.final_result = None

        st.rerun()