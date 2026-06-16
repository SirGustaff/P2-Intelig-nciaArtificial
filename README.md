# Recrutador Inteligente

Avaliador técnico baseado em evidências usando IA (Groq + Llama 3.3).

## Funcionalidades

- Upload de currículo (PDF, DOCX, TXT) ou colagem de texto
- Análise inicial de competências e lacunas
- Até 2 rodadas de perguntas de Verificação (VFU)
- Relatório final com score, radar de competências, evidências e justificativa
- Exportação do relatório em PDF
- Dashboard interativo com métricas

## Como usar

```bash
pip install -r requirements.txt
streamlit run app.py
```

1. Insira sua [API Key da Groq](https://console.groq.com)
2. Cole a descrição da vaga
3. Envie ou cole o currículo
4. Clique em **Iniciar Avaliação**
5. Responda às perguntas de verificação
6. Consulte o relatório final e baixe em PDF

## Estrutura

```
app.py              -- Aplicação principal (Streamlit)
requirements.txt    -- Dependências
```

## Stack

- **Frontend**: Streamlit
- **IA**: Groq API (llama-3.3-70b-versatile)
- **Extração**: pypdf, python-docx
- **Gráficos**: Plotly
- **Relatório PDF**: ReportLab
