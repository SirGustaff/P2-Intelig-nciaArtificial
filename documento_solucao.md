# Solução Recrutador Inteligente

**Atividade Avaliativa P2** — Implementação de LLM para Fluxograma Evidence-to-Decision

**Disciplina:** Inteligência Artificial  
**Data:** 16/06/2026  
**Grupo:** — *[inserir nomes]* —

---

## 1. Introdução

A tomada de decisão em recrutamento e seleção tradicionalmente depende da avaliação subjetiva de recrutadores humanos, o que pode introduzir vieses e inconsistências. A metodologia **Evidence-to-Decision (EtD)** propõe uma abordagem estruturada e baseada em evidências para avaliar candidatos, garantindo que cada decisão seja fundamentada em dados concretos e verificáveis.

Este trabalho apresenta uma solução computacional que implementa o fluxograma EtD utilizando **Large Language Models (LLMs)** — especificamente o modelo **Llama 3.3 (70B)** da Meta, acessado via API da **Groq**. A solução foi desenvolvida como uma aplicação web interativa em **Python com Streamlit**, permitindo que recrutadores insiram descrições de vagas e currículos, e conduzam uma entrevista baseada em evidências com até duas rodadas de Verificação (VFU), culminando em um relatório final estruturado.

---

## 2. Metodologia Evidence-to-Decision

### 2.1 Fundamentos

A metodologia Evidence-to-Decision segue um fluxo sistemático composto pelas seguintes etapas:

1. **Análise Inicial:** O sistema analisa a descrição da vaga e o currículo do candidato, extraindo:
   - Competências exigidas pela vaga
   - Competências comprovadas pelo candidato
   - Lacunas identificadas

2. **Verificação (VFU — Verification Follow-Up):** O sistema gera perguntas específicas para aprofundar evidências sobre competências críticas, seguindo o princípio de que alegações sem evidências concretas devem ser desconsideradas.

3. **Decisão:** Com base nas evidências coletadas nas rodadas de VFU, o sistema decide se:
   - Há necessidade de mais esclarecimentos (nova VFU)
   - As evidências são suficientes para gerar o relatório final

4. **Relatório Final:** O sistema produz um relatório estruturado contendo:
   - Classificação do candidato em relação à vaga
   - Recomendação (Avançar / Não Avançar)
   - Score de compatibilidade (0-100%)
   - Nível de confiança da avaliação
   - Radar de competências com notas por habilidade
   - Evidências detectadas durante a avaliação
   - Lacuna principal e perfil de deficiência
   - Justificativa analítica (rationale)

### 2.2 Fluxograma Implementado

O fluxo abaixo representa a implementação computacional da metodologia:

```
                    ┌──────────────────────┐
                    │   Descrição da Vaga  │
                    │   + Currículo        │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │   Análise Inicial    │
                    │  (Competências e     │
                    │   Lacunas)           │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │   Geração da 1ª VFU  │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  Candidato Responde  │
                    └──────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │  LLM Avalia Resposta │
                    ├──────────────────────┤
                    │ ▼ VFU?  ───→ round≤2?│──→ Nova VFU
                    │         └──→ Forçar   │
                    │ ▼ Final?──→ Relatório │
                    └──────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │   Relatório Final    │
                    │  + Dashboard + PDF   │
                    └──────────────────────┘
```

---

## 3. Arquitetura da Solução

### 3.1 Visão Geral

A aplicação segue uma arquitetura de camadas:

```
┌─────────────────────────────────────────────┐
│              Interface Web                  │
│            (Streamlit - app.py)             │
├─────────────────────────────────────────────┤
│          Camada de Processamento            │
│   Análise Inicial │ VFU │ Relatório Final  │
├─────────────────────────────────────────────┤
│          Camada de Integração LLM           │
│        Groq API → Llama 3.3 (70B)          │
├─────────────────────────────────────────────┤
│         Camada de Extração de Dados         │
│     pypdf │ python-docx │ TXT              │
├─────────────────────────────────────────────┤
│         Camada de Geração de Relatório      │
│      ReportLab (PDF) │ Plotly (Gráficos)   │
└─────────────────────────────────────────────┘
```

### 3.2 Tecnologias Utilizadas

| Componente | Tecnologia | Versão | Função |
|---|---|---|---|
| Frontend | Streamlit | 1.58 | Interface web interativa |
| Modelo de Linguagem | Llama 3.3 (70B) | — | Avaliação e geração de perguntas |
| API de IA | Groq | 1.4 | Acesso ao LLM com baixa latência |
| Extração PDF | pypdf | 6.13 | Leitura de currículos em PDF |
| Extração DOCX | python-docx | 1.2 | Leitura de currículos em Word |
| Gráficos | Plotly | 6.8 | Radar de competências |
| Relatório PDF | ReportLab | 4.5 | Exportação do relatório |
| Manipulação de Dados | pandas | 3.0 | Estruturação de dados |

---

## 4. Implementação

### 4.1 Estrutura do Código

O sistema é implementado em um único arquivo (`app.py`) organizado nas seguintes seções:

```
app.py
├── Configuração da Página (Streamlit)
├── Session State (variáveis de estado)
├── System Prompt (instruções para o LLM)
├── Utilitários (cliente Groq, extração JSON)
├── Extração de Currículo (PDF, DOCX, TXT)
├── Análise Inicial
├── Geração de VFU (Verification Follow-Up)
├── Processamento de Respostas
├── Geração Forçada de Relatório
├── Tela de Configuração (entrada de dados)
├── Tela de Interação (perguntas e respostas)
├── Tela de Relatório (dashboard e exportação)
└── Geração de PDF
```

### 4.2 Componentes Principais

#### 4.2.1 Prompt de Sistema (SYSTEM_PROMPT)

O coração da metodologia é o prompt de sistema que instrui o LLM a agir como um **Avaliador Técnico Especialista** em recrutamento baseado em evidências. As regras fundamentais são:

1. Ignorar jargões e respostas genéricas
2. Procurar evidências concretas
3. Validar experiências técnicas
4. Detectar lacunas
5. Limitar a 2 rodadas de VFU
6. Retornar exclusivamente JSON estruturado

#### 4.2.2 Extração de JSON Robusta

A função `extract_json()` implementa um algoritmo de rastreamento por profundidade de chaves (`{`/`}`) que localiza e extrai o primeiro objeto JSON completo do texto retornado pelo LLM, garantindo resiliência mesmo quando o modelo inclui texto adicional.

```python
def extract_json(text):
    try:
        return json.loads(text)
    except ValueError:
        # Rastreamento por profundidade para extrair
        # o primeiro JSON completo do texto
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
        raise ValueError("Resposta JSON inválida")
```

#### 4.2.3 Gerenciamento de Conversação

O histórico da conversa é mantido no `st.session_state` do Streamlit, preservando o contexto completo entre as chamadas ao LLM. A cada interação:

1. A resposta do candidato é adicionada como mensagem `"user"`
2. Um prompt de controle é adicionado como mensagem `"system"` instruindo o LLM a decidir entre nova VFU ou relatório final
3. O LLM processa o histórico completo e retorna sua decisão
4. A resposta do LLM é armazenada como mensagem `"assistant"`

#### 4.2.4 Extração de Currículo

Suporte a três formatos de arquivo:

- **PDF:** Utiliza `PdfReader` do `pypdf` para extrair texto página a página
- **DOCX:** Utiliza `Document` do `python-docx` para extrair parágrafos
- **TXT:** Leitura direta com decodificação UTF-8

#### 4.2.5 Geração de Relatório PDF

O relatório final é exportado em PDF utilizando `ReportLab`, contendo:

- Título e cabeçalho
- Classificação, recomendação e compatibilidade
- Justificativa analítica

---

## 5. Fluxo de Execução

### 5.1 Tela de Configuração

O usuário insere:
1. **API Key da Groq** (campo senha)
2. **Descrição da vaga** (textarea)
3. **Currículo** (upload PDF/DOCX/TXT ou colagem de texto)

### 5.2 Inicialização da Avaliação

Ao clicar em "Iniciar Avaliação Baseada em Evidências":

1. Validação dos campos obrigatórios
2. Chamada à função `run_initial_analysis()` que envia vaga + currículo ao LLM para extrair competências e lacunas
3. Chamada à função `start_evaluation()` que gera a primeira pergunta VFU
4. Transição para a tela de interação

### 5.3 Tela de Interação (VFU)

Para cada rodada de VFU:
1. Exibição da pergunta gerada pelo LLM
2. O candidato digita sua resposta
3. A resposta é processada por `process_candidate_answer()`
4. O LLM avalia a resposta e decide:
   - **Se "final":** Gera o relatório final
   - **Se "vfu" e round < 2:** Gera nova pergunta VFU
   - **Se "vfu" e round ≥ 2:** Força a geração do relatório final
   - **Se status desconhecido:** Força a geração do relatório final (segurança)

### 5.4 Tela de Relatório

O relatório final exibe:
- **Métricas:** Compatibilidade, confiança, classificação, recomendação
- **Barra de progresso:** Representação visual do score
- **Lacuna principal e perfil de deficiência**
- **Radar de competências:** Gráfico polar interativo (Plotly)
- **Evidências detectadas:** Lista de evidências concretas
- **Justificativa analítica:** Explicação detalhada da decisão
- **Exportação PDF:** Botão para download do relatório
- **Histórico da sessão:** Tabela com avaliações anteriores

---

## 6. Exemplos de Uso

### 6.1 Exemplo de VFU

Entrada do LLM (pergunta gerada):
> "Com base na sua experiência em Python listada no currículo, descreva um projeto específico onde você utilizou programação orientada a objetos e como isso impactou o resultado do projeto?"

### 6.2 Exemplo de Relatório Final (JSON)

```json
{
    "status": "final",
    "classificacao": "Totalmente Alinhado",
    "recomendacao": "Avançar",
    "compatibilidade": 85,
    "lacuna_principal": "Experiência limitada com Docker em produção",
    "perfil_deficiencia": "Conhecimento teórico de Docker, sem prática em orquestração",
    "confianca": "Alto",
    "competencias": {
        "Python": 90,
        "SQL": 80,
        "Cloud": 70,
        "Docker": 75,
        "Comunicação": 85
    },
    "evidencias": [
        "Implementou pipeline ETL processando 500k registros/dia em Python",
        "Liderou migração de banco SQL Server para PostgreSQL"
    ],
    "rationale": "O candidato demonstra domínio técnico em Python e SQL com evidências concretas..."
}
```

---

## 7. Como Executar

### 7.1 Pré-requisitos

- Python 3.10+
- Conta na [Groq Console](https://console.groq.com) para obter API Key

### 7.2 Instalação

```bash
pip install -r requirements.txt
```

### 7.3 Execução

```bash
streamlit run app.py
```

### 7.4 Configuração

1. Acesse a URL exibida no terminal (geralmente `http://localhost:8501`)
2. Insira sua API Key da Groq no campo apropriado
3. Cole a descrição da vaga
4. Faça upload do currículo ou cole o texto

---

## 8. Considerações Técnicas

### 8.1 Limitações

- O modelo Llama 3.3 70B pode ocasionalmente retornar JSON malformado; o sistema possui fallback para extração robusta
- Limite de 2 VFUs por avaliação (configurável no SYSTEM_PROMPT)
- Depende de conexão com internet para acessar a API Groq
- A qualidade da avaliação depende da clareza da descrição da vaga e do currículo

### 8.2 Segurança

- A API Key é armazenada apenas na sessão do usuário (não persiste em disco)
- Nenhum dado é armazenado em servidores externos além das chamadas à API Groq
- O código não expõe keys ou secrets no repositório

---

## 9. Conclusão

A solução implementa com sucesso a metodologia Evidence-to-Decision utilizando LLM, automatizando o processo de avaliação de candidatos com base em evidências concretas. O sistema conduz uma entrevista estruturada com até duas rodadas de verificação, coletando evidências detalhadas antes de gerar um relatório final completo com dashboard interativo e exportação PDF.

A arquitetura modular permite fácil manutenção e extensão, como a adição de novos critérios de avaliação, suporte a mais formatos de currículo, ou integração com sistemas de ATS (Applicant Tracking System).

---

## 10. Referências

- Groq API Documentation. Disponível em: https://console.groq.com/docs
- Streamlit Documentation. Disponível em: https://docs.streamlit.io
- Meta Llama 3.3 Model Card. Disponível em: https://llama.meta.com
- Evidence-to-Decision Framework. Diretrizes para avaliação baseada em evidências.
