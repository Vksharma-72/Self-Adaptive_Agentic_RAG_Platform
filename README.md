# Enterprise Agentic RAG: LangGraph · Guardrails · LLM Gateway · RAGAS Evals

A production-grade, state-of-the-art Retrieval-Augmented Generation (RAG) system built for speed, scalability, and deep observability. This platform leverages **LangGraph** to handle complex reasoning and a fully local, cloud-agnostic stack for document intelligence.

## 🌟 Vision

Most RAG systems fail because they treat every query the same. Our **Agentic RAG** distinguishes between:
1. **Conversational Queries**: "Hi", "Who are you?", "What did I just say?"
2. **Technical Queries**: "How do I configure Intel SRIOV on Kubernetes?"

By using a **Planner-Retriever-Responder** architecture, we ensure that technical answers are always grounded in "True Data" while conversational interactions remain fluid and fast.

## 🏗️ System Architecture

The system follows a modular, event-driven architecture with clear separation of concerns:

![System Architecture](./ARCHITECTURE.md#enterprise-agentic-rag-langgraph--guardrails--llm-gateway--ragas-evals)

### Key Components:

1.  **Interface Layer**: Streamlit-based Chat UI and Evaluation UI
2.  **API + Safety Gate**: FastAPI endpoint protected by NeMo Guardrails
3.  **LangGraph Agentic Core**: Planner (Intent Classification) → Retriever (Vector Search + Reranking) → Responder (Answer Generation)
4.  **Retrieval Layer**: Qdrant Cloud Vector DB + FlashRank Local Reranker
5.  **LLM Gateway**: Portkey for resilient, observable LLM calls (Groq Llama 3.3 70B primary, Llama 3.1 8B fallback)
6.  **Ingestion Pipeline**: Document Loaders → Semantic Chunker → Gemini Embeddings → Qdrant
7.  **Observability**: Pydantic Logfire (distributed tracing) + LangSmith (LLM orchestration tracing)
8.  **Evaluation Suite**: RAGAS metrics + DeepEval Tool Correctness + Golden Dataset

## 🔑 Key Features

- **Agentic Query Planning**: Distinguishes between conversational and technical queries to avoid unnecessary retrieval.
- **Two-Stage Retrieval**: Fast vector search (Qdrant) followed by semantic reranking (FlashRank) for precision.
- **LLM Gateway with Portkey**: Automatic retries, fallbacks, caching, and observability for LLM calls.
- **NeMo Guardrails**: Pre-LLM safety layer that blocks jailbreaks, off-topic queries, and PII leaks.
- **Comprehensive Observability**: End-to-end tracing with Logfire and LangSmith.
- **Production-Grade Evaluation**: RAGAS metrics (Faithfulness, Answer Relevancy, Context Precision, Recall, Answer Correctness) and Tool Correctness via DeepEval.
- **Modular Ingestion Pipeline**: Supports PDF, HTML, DOCX, PPTX, TXT with local parsing (no external OCR).
- **Conversation Memory**: Persistent chat history via LangGraph's MemorySaver.
- **Cost Optimization**: Uses Groq's fast, low-cost models with intelligent fallback and caching.

## 📂 Project Structure

```
Enterprise-Agentic-RAG/
├── app/                    # Core Python package (FastAPI backend, agents, services)
│   ├── agents/             # LangGraph agent nodes (planner, retriever, responder)
│   ├── gateway/            # LLM Gateway integration (Portkey)
│   ├── guardrails/         # NeMo Guardrails configuration
│   ├── ingestion/          # Document loading, chunking, embedding
│   ├── services/           # Retrieval, embedding services
│   ├── config.py           # Configuration management
│   └── main.py             # FastAPI entry point
├── ui/                     # Streamlit interfaces
│   ├── app.py              # Main chat UI
│   └── st_cloud_ui.py      # Evaluation UI
├── evals/                  # Evaluation pipelines and golden datasets
│   ├── app.py              # Streamlit eval dashboard
│   ├── pipeline.py         # Phase 1: Live response generation
│   ├── metrics.py          # Phase 2: RAGAS metric scoring
│   ├── guardrails_eval.py  # Guardrails testing
│   ├── data_parser.py      # Golden dataset builder
│   └── __init__.py
├── DATA/                   # Ground-truth documentation for ingestion
│   ├── true_data/          # verified documents
│   └── noisy_data/         # distractor documents
├── processed_data/         # Output of ingestion pipeline (JSON chunks)
├── notebooks/              # Jupyter notebooks for experimentation
├── DOCS/                   # Detailed documentation (see below)
├── requirements.txt        # Python dependencies
├── requirements-prod.txt   # Production dependencies
├── Dockerfile              # Containerization
├── ARCHITECTURE.md         # System architecture diagrams
└── README.md               # This file
```

### Documentation (`DOCS/`)

- `01_SYSTEM_OVERVIEW.md`: High-level vision and architecture
- `02_INGESTION_ENGINE.md`: Document parsing, chunking, and vectorization
- `03_NODE_INTELLIGENCE.md`: LangGraph agent nodes (Planner, Retriever, Responder)
- `04_TRACING_AND_OBSERVABILITY.md`: Logfire and LangSmith integration
- `05_ENVIRONMENT_VARIABLES.md`: Required environment variables
- `06_KNOWN_GOTCHAS.md`: Common issues and troubleshooting
- `07_FLASHRANK_RERANKING.md`: Local semantic reranking with FlashRank
- `08_GUARDRAILS.md`: NeMo Guardrails implementation (jailbreak, off-topic, dialog control)
- `09_LLM_GATEWAY.md`: Portkey integration for resilient LLM calls
- `10_EVALS.md`: RAGAS evaluation framework overview
- `11_EVALS_PIPELINE.md`: Detailed evaluation pipeline (golden dataset, two-phase testing)

## ⚙️ Setup and Installation

### Prerequisites

- Python 3.9+
- Docker (optional, for containerized deployment)
- Groq API key (for Llama 3 models)
- Portkey API key (for LLM gateway)
- Qdrant Cloud account (or local instance)
- Google Gemini API key (for embeddings)
- Pydantic Logfire token (for distributed tracing)
- LangSmith API key (for LLM tracing)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Vksharma-72/Enterprise-Agentic-RAG.git
   cd Enterprise-Agentic-RAG
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. (Optional) Build and run with Docker:
   ```bash
   docker build -t enterprise-agentic-rag .
   docker run -p 8000:8000 --env-file .env enterprise-agentic-rag
   ```

## 🚀 Usage

### Start the Backend API

```bash
uvicorn app.main:app --reload --port 8000
```

### Start the Streamlit Chat UI

```bash
streamlit run ui/app.py
```

### Start the Evaluation Dashboard

```bash
streamlit run evals/app.py
```

### Run the Ingestion Pipeline

```bash
python -m app.ingestion.processor DATA --wipe
```

### Run the Evaluation Pipeline

1. Start the backend (`uvicorn app.main:app --reload --port 8000`)
2. Launch the evaluation dashboard (`streamlit run evals/app.py`)
3. Follow the three tabs:
   - **Ground Truth**: Review the 15 golden Q&A pairs and 6 guardrails test cases
   - **Live Pipeline**: Click "Run Live Pipeline" to collect real responses from the API
   - **Eval Metrics**: Click "Run Eval Metrics" to compute RAGAS scores (takes ~50 min on free tier)

## 🔧 Configuration and Environment Variables

See [DOCS/05_ENVIRONMENT_VARIABLES.md](./DOCS/05_ENVIRONMENT_VARIABLES.md) for a complete list.

Key variables:
- `GROQ_API_KEY`: Primary Groq API key (for Llama 3.3 70B)
- `GROQ_FALLBACK_API_KEY`: Fallback Groq API key (for Llama 3.1 8B)
- `PORTKEY_API_KEY`: Portkey API key for LLM gateway
- `PORTKEY_VIRTUAL_KEY`: Portkey virtual key (if applicable)
- `QDRANT_URL`: Qdrant Cloud instance URL
- `QDRANT_API_KEY`: Qdrant API key
- `GEMINI_API_KEY`: Google Gemini API key for embeddings
- `LOGFIRE_TOKEN`: Pydantic Logfire token for distributed tracing
- `LANGCHAIN_API_KEY`: LangSmith API key for LLM tracing
- `LANGCHAIN_PROJECT`: LangSmith project name
- `BACKEND_URL`: URL of the FastAPI backend (for UI)
- `JUDGE_GROQ`: Separate Groq API key for evaluation judge (Llama 3.1 8B) to avoid rate limits

## 📊 Evaluation

The evaluation system uses a golden dataset of 15 technical questions and 6 guardrails test cases. It runs in two phases:

1.  **Live Pipeline**: Sends each question to the running API, capturing responses, retrieved contexts, and tool usage.
2.  **RAGAS Metrics**: Uses a separate judge LLM (Llama 3.1 8B) to score:
    - **Faithfulness**: Does the answer stick to the retrieved context? (0-1)
    - **Answer Relevancy**: Does the answer address the question? (0-1)
    - **Context Precision**: Are relevant chunks ranked first? (0-1)
    - **Context Recall**: Did we fetch all needed chunks? (0-1)
    - **Answer Correctness**: Does the answer match the ground truth? (0-1)
    - **Tool Correctness**: Did the agent call the right tool? (Jaccard score, 0-1)

See [DOCS/10_EVALS.md](DOCS/10_EVALS.md) and [DOCS/11_EVALS_PIPELINE.md](DOCS/11_EVALS_PIPELINE.md) for details.

## 🚧 Future Plans

As mentioned in the project vision, upcoming enhancements include:

- **Turbovec**: Advanced vector optimization for faster, more efficient retrieval
- **Turboquant**: Quantization techniques to reduce LLM inference cost and latency
- **Enhanced LLM Guardrails**: Additional safety layers for PII detection, toxicity, and jailbreak resilience
- **UI Improvements**: 
  - File upload interface for dynamic document ingestion
  - Enhanced source citations with page numbers and highlights
  - Conversation sharing and export features
- **Cost Optimization**: 
  - Dynamic model routing based on query complexity
  - Response caching with semantic similarity
  - Token usage optimization through prompt compression
- **Multi-Modal Support**: Extending ingestion to handle images, diagrams, and tables within documents
- **Deployment Automation**: Helm charts and Terraform scripts for cloud-agnostic deployment

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangGraph](https://langchain-ai.github.io/langgraph/) for agentic orchestration
- [NeMo Guardrails](https://docs.nvidia.com/nemo-framework/user-guide/latest/nemo-framework/getting-started/what-is-nemo-guardrails.html) for AI safety
- [Portkey](https://www.portkey.ai/) for LLM gateway and observability
- [RAGAS](https://github.com/explodinggradients/ragas) for RAG evaluation
- [Qdrant](https://qdrant.tech/) for vector search
- [FlashRank](https://github.com/OptimalScale/FlashRank) for local reranking
- [Groq](https://groq.com/) for fast LLM inference
- [Google Gemini](https://ai.google.dev/) for embeddings
- [Pydantic Logfire](https://logfire.pydantic.dev/) for distributed tracing
- [LangSmith](https://smith.langchain.com/) for LLM observability

---
*Built with ❤️ by the Vishnu Kumar Sharma*