# ==========================================================
# RECRUTADOR INTELIGENTE
# app.py
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


SYSTEM_PROMPT = """
Você é um Avaliador Técnico Especialista em recrutamento baseado em evidências.

OBJETIVO:
Avaliar candidatos usando a metodologia Evidence-to-Decision, analisando de forma justa a relação entre fundamentos teóricos/estruturais e ferramentas específicas de execução.

DIRETRIZ DE COGNIÇÃO (BLOQUEIO DE FALSO-NEGATIVO):
1. CLASSIFICAÇÃO DE CONCEITOS: Separe mentalmente os requisitos da vaga em:
   - Competências Estruturais (Core): O fundamento técnico essencial, a lógica de pensamento, os conceitos de arquitetura ou as linguagens de base necessárias para a função.
   - Ferramental de Execução (Secundário): Os frameworks, softwares específicos, bibliotecas, metodologias proprietárias ou ferramentas de mercado usadas para aplicar o fundamento.

2. CRITÉRIO DE PARADA IMEDIATA (0 VFUs): Você só pode encerrar a análise de imediato com status "final" (reprovação direta) se o candidato demonstrar incompatibilidade total nos pilares das Competências Estruturais (Core). Ou seja, quando o histórico dele pertence a uma disciplina ou profissão completamente diferente da vaga.

3. OBRIGATORIEDADE DE INVESTIGAÇÃO (1 ou 2 VFUs): Se o candidato demonstra possuir a base conceitual, a lógica estrutural ou a linguagem de base (Core), mas omitiu ou não detalhou o Ferramental de Execução específico (frameworks ou softwares complementares), você está PROIBIDO de reprová-lo de imediato. Você DEVE obrigatoriamente definir o status como "vfu" e gerar uma pergunta para investigar se ele possui experiência prática ou adaptabilidade com o ecossistema solicitado.

NUNCA RETORNE TEXTO FORA DO JSON. O RETORNO DEVE SER APENAS O OBJETO JSON PURO.

===========================
FORMATO SE DECIDIR POR VFU (status: "vfu")
===========================
{
    "status": "vfu",
    "round": 1,
    "question": "Sua pergunta curta, contextualizada e objetiva aqui"
}

===========================
FORMATO SE DECIDIR ENCERRAR (status: "final")
===========================
{
    "status": "final",
    "classificacao": "Sua classificação aqui (ex: Totalmente Alinhado, Alinhamento Parcial, Não Alinhado)",
    "recomendacao": "Sua recomendação aqui (ex: Avançar, Guardar em Banco, Descontinuar)",
    "compatibilidade": [INSIRA_AQUI_UM_INTEIRO_DE_0_A_100_BASEADO_NA_SUA_AVALIACAO],
    "lacuna_principal": "Descrição da principal lacuna encontrada",
    "perfil_deficiencia": "Breve descrição dos pontos fracos do perfil",
    "confianca": "Nível de confiança na análise (ex: Alto, Médio, Baixo)",
    "competencias": {
        "NomeDaCompetencia1": [NOTA_DE_0_A_100],
        "NomeDaCompetencia2": [NOTA_DE_0_A_100]
    },
    "evidencias": [
        "Evidência concreta 1 encontrada no texto",
        "Evidência concreta 2 encontrada no texto"
    ],
    "rationale": "Justificativa analítica detalhada da decisão"
}
"""

# ==========================================================
# UTILITÁRIOS
# ==========================================================

def create_client():
    return Groq(api_key=st.session_state.api_key)

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
                        return json.loads(text[start : i + 1])
                    except ValueError:
                        start = -1
        raise ValueError("Resposta JSON inválida recebida do modelo.")

# ==========================================================
# CHAMADA GROQ
# ==========================================================

def call_llm(messages):
    client = create_client()
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=0.1,  # Reduzido para maior consistência no JSON
        max_completion_tokens=2500
    )
    return response.choices[0].message.content

# ==========================================================
# EXTRAÇÃO DE TEXTO
# ==========================================================

def extract_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def extract_docx(uploaded_file):
    document = Document(uploaded_file)
    return "\n".join(p.text for p in document.paragraphs)

def extract_resume(uploaded_file):
    extension = uploaded_file.name.split(".")[-1].lower()
    if extension == "pdf":
        return extract_pdf(uploaded_file)
    if extension == "docx":
        return extract_docx(uploaded_file)
    return uploaded_file.read().decode("utf-8")

# ==========================================================
# ANÁLISE INICIAL
# ==========================================================

def run_initial_analysis():
    prompt = f"""
Analise a descrição da vaga fornecida e o currículo do candidato para mapear os escopos iniciais.

DESCRIÇÃO DA VAGA:
{st.session_state.job_description}

CURRÍCULO:
{st.session_state.resume_text}

Instruções: Monte listas diretas de competências exigidas, validadas e lacunas identificadas.
Retorne estritamente o formato JSON estruturado abaixo, sem dados populados de exemplo no prompt.

{{
 "competencias_exigidas": [],
 "competencias_comprovadas": [],
 "lacunas": []
}}
"""
    messages = [
        {"role": "system", "content": "Você é um assistente de RH técnico focado em extração de dados brutos. Retorne apenas JSON válido."},
        {"role": "user", "content": prompt}
    ]
    response = call_llm(messages)
    return extract_json(response)

# ==========================================================
# AVALIAÇÃO INICIAL DINÂMICA (PODE GERAR 0 VFUs OU INICIAR VFU)
# ==========================================================

def start_evaluation():
    recruiter_prompt = f"""
Descrição da vaga:
{st.session_state.job_description}

Currículo:
{st.session_state.resume_text}

Analise os documentos. Decida se é necessária uma pergunta de validação (VFU) para esclarecer dúvidas sobre as evidências, ou se as informações atuais já são plenamente suficientes para emitir o veredito final.

- Se precisar de esclarecimentos, retorne o JSON com status "vfu" e configure a propriedade "round" como 1.
- Se não houver necessidade de perguntas (0 VFUs necessárias), retorne imediatamente o formato estruturado completo com o status "final".
"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": recruiter_prompt}
    ]
    
    response = call_llm(messages)
    result = extract_json(response)
    
    st.session_state.conversation = messages + [{"role": "assistant", "content": response}]
    
    if result.get("status") == "vfu":
        st.session_state.vfu_round = 1
    
    return result

# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:
    st.title("⚙️ Configurações")
    st.session_state.api_key = st.text_input("API Key Groq", type="password")
    st.markdown("---")
    st.info(
        """
        Recrutador Inteligente
        Metodologia: Evidence-to-Decision
        Modelo: llama-3.3-70b-versatile
        """
    )

# ==========================================================
# TELA CONFIGURAÇÃO
# ==========================================================

if st.session_state.phase == "config":
    st.title("🎯 Recrutador Inteligente")
    st.subheader("Descrição da Vaga")
    st.session_state.job_description = st.text_area("Cole a descrição da vaga", height=200)

    st.subheader("Currículo")
    uploaded_file = st.file_uploader("Enviar PDF, DOCX ou TXT", type=["pdf", "docx", "txt"])

    if uploaded_file:
        try:
            st.session_state.resume_text = extract_resume(uploaded_file)
            st.success("Currículo carregado com sucesso!")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.session_state.resume_text = st.text_area(
        "Ou cole o currículo manualmente",
        value=st.session_state.resume_text,
        height=200
    )

    if st.button("🚀 Iniciar Avaliação Baseada em Evidências", use_container_width=True):
        if not st.session_state.api_key:
            st.error("Informe sua API Key da Groq.")
            st.stop()
        if not st.session_state.job_description.strip():
            st.error("Informe a descrição da vaga.")
            st.stop()
        if not st.session_state.resume_text.strip():
            st.error("Informe o currículo.")
            st.stop()

        try:
            with st.spinner("Analisando perfil técnico..."):
                analysis = run_initial_analysis()
                st.session_state.analysis_result = analysis

                # Avaliação dinâmica inicial
                evaluation_step = start_evaluation()

                if evaluation_step.get("status") == "final":
                    st.session_state.final_result = evaluation_step
                    st.session_state.history.append({
                        "Classificação": evaluation_step.get("classificacao"),
                        "Compatibilidade": evaluation_step.get("compatibilidade"),
                        "Recomendação": evaluation_step.get("recomendacao")
                    })
                    st.session_state.phase = "report"
                else:
                    st.session_state.current_question = evaluation_step
                    st.session_state.phase = "interaction"
            st.rerun()
        except Exception as e:
            st.error(f"Erro durante a avaliação inicial: {e}")

# ==========================================================
# PROCESSAMENTO DAS RESPOSTAS
# ==========================================================

def process_candidate_answer(answer):
    st.session_state.conversation.append({"role": "user", "content": answer})
    
    control_prompt = f"""
Rodada atual de VFU: {st.session_state.vfu_round}

Analise a resposta fornecida pelo candidato.
Decida com base nas evidências coletadas até aqui:
1. Se ainda houver lacunas críticas que necessitem de mais esclarecimento E a rodada atual for menor que 2, gere uma nova pergunta definindo o status como "vfu" e incremente o valor de "round".
2. Caso contrário, finalize a avaliação estruturando por completo o relatório final (status: "final").

Lembre-se: O limite máximo absoluto é de 2 rodadas de VFUs. Não extrapole este teto.
Retorne estritamente o objeto JSON apropriado seguindo as diretrizes do sistema.
"""
    st.session_state.conversation.append({"role": "system", "content": control_prompt})
    response = call_llm(st.session_state.conversation)
    result = extract_json(response)
    st.session_state.conversation.append({"role": "assistant", "content": response})
    return result

def force_final_report():
    st.session_state.conversation.append({
        "role": "user",
        "content": "Atingimos o critério de encerramento da coleta de fatos. Construa imediatamente o relatório de avaliação técnica final estruturado em JSON conforme as regras estabelecidas."
    })
    response = call_llm(st.session_state.conversation)
    result = extract_json(response)
    st.session_state.conversation.append({"role": "assistant", "content": response})
    return result

# ==========================================================
# TELA DE INTERAÇÃO
# ==========================================================

if st.session_state.phase == "interaction":
    st.title("🧠 Entrevista Baseada em Evidências")

    if st.session_state.analysis_result:
        with st.expander("📊 Análise Inicial de Escopo"):
            col1, col2 = st.columns(2)
            with col1:
                st.success("Competências mapeadas inicialmente")
                for item in st.session_state.analysis_result.get("competencias_comprovadas", []):
                    st.write(f"✅ {item}")
            with col2:
                st.warning("Lacunas mapeadas inicialmente")
                for item in st.session_state.analysis_result.get("lacunas", []):
                    st.write(f"⚠️ {item}")

    st.markdown("---")
    st.info(f"Rodada VFU ativa: {st.session_state.vfu_round} de um teto máximo de 2.")

    question_data = st.session_state.current_question
    question = question_data.get("question", "Pergunta indisponível.")

    with st.container(border=True):
        st.subheader("Pergunta de Verificação do Especialista")
        st.write(question)

    answer = st.text_area("Resposta / Contra-argumentação do candidato", height=180)
    submit = st.button("Enviar Resposta", use_container_width=True)

    if submit:
        if not answer.strip():
            st.warning("Por favor, digite uma resposta para continuar.")
            st.stop()

        try:
            with st.spinner("Avaliando solidez das evidências..."):
                result = process_candidate_answer(answer)

                if result.get("status") == "final":
                    st.session_state.final_result = result
                    st.session_state.history.append({
                        "Classificação": result.get("classificacao"),
                        "Compatibilidade": result.get("compatibilidade"),
                        "Recomendação": result.get("recomendacao")
                    })
                    st.session_state.phase = "report"
                    st.rerun()

                elif result.get("status") == "vfu":
                    if st.session_state.vfu_round >= 2:
                        final_report = force_final_report()
                        st.session_state.final_result = final_report
                        st.session_state.history.append({
                            "Classificação": final_report.get("classificacao"),
                            "Compatibilidade": final_report.get("compatibilidade"),
                            "Recomendação": final_report.get("recomendacao")
                        })
                        st.session_state.phase = "report"
                    else:
                        st.session_state.vfu_round += 1
                        st.session_state.current_question = result
                    st.rerun()
                else:
                    final_report = force_final_report()
                    st.session_state.final_result = final_report
                    st.session_state.phase = "report"
                    st.rerun()
        except Exception as e:
            st.error(f"Erro ao processar fluxo de resposta: {e}")

# ==========================================================
# GERADOR PDF
# ==========================================================

def generate_pdf(result):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(temp_file.name)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Relatório de Avaliação Técnica", styles["Title"]))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"<b>Classificação:</b> {result.get('classificacao')}", styles["BodyText"]))
    elements.append(Paragraph(f"<b>Recomendação:</b> {result.get('recomendacao')}", styles["BodyText"]))
    elements.append(Paragraph(f"<b>Compatibilidade Geral:</b> {result.get('compatibilidade')}%", styles["BodyText"]))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Justificativa Analítica</b>", styles["Heading2"]))
    elements.append(Paragraph(result.get("rationale", ""), styles["BodyText"]))

    doc.build(elements)
    return temp_file.name

# ==========================================================
# TELA DO RELATÓRIO FINAL
# ==========================================================

if st.session_state.phase == "report":
    result = st.session_state.final_result
    st.title("📊 Relatório de Desempenho Final")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Compatibilidade", f"{result.get('compatibilidade', 0)}%")
    with col2:
        st.metric("Grau de Confiança", result.get("confianca", "-"))
    with col3:
        st.metric("Classificação", result.get("classificacao", "-"))
    with col4:
        st.metric("Recomendação", result.get("recomendacao", "-"))

    st.progress(float(result.get("compatibilidade", 0)) / 100)
    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Gargalo / Principal Lacuna")
        st.warning(result.get("lacuna_principal", "-"))
    with col_b:
        st.subheader("Perfil de Deficiência Detectado")
        st.info(result.get("perfil_deficiencia", "-"))

    st.markdown("---")
    st.subheader("Mapeamento Radial de Competências")
    skills = result.get("competencias", {})
    if skills:
        df = pd.DataFrame({"Competência": list(skills.keys()), "Nota": list(skills.values())})
        fig = px.line_polar(df, r="Nota", theta="Competência", line_close=True)
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader("Fatos & Evidências Encontradas")
    evidencias = result.get("evidencias", [])
    if evidencias:
        for evidence in evidencias:
            st.success(evidence)

    st.markdown("---")
    st.subheader("Justificativa Estruturada")
    st.write(result.get("rationale", "Dados analíticos não gerados."))

    st.markdown("---")
    try:
        pdf_path = generate_pdf(result)
        with open(pdf_path, "rb") as pdf_file:
            st.download_button(
                label="📄 Exportar Parecer em PDF",
                data=pdf_file,
                file_name="relatorio_avaliacao_tecnica.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    except Exception as e:
        st.error(f"Erro ao renderizar PDF: {e}")

    st.markdown("---")
    st.subheader("Histórico da Sessão")
    if st.session_state.history:
        st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True)
    else:
        st.info("Sem registros no histórico local.")

    if st.button("🔄 Avaliar Novo Candidato", use_container_width=True):
        st.session_state.phase = "config"
        st.session_state.job_description = ""
        st.session_state.resume_text = ""
        st.session_state.conversation = []
        st.session_state.current_question = ""
        st.session_state.vfu_round = 0
        st.session_state.analysis_result = None
        st.session_state.final_result = None
        st.rerun()