# DjangoForge 🚀

**DjangoForge** is an advanced LLM-powered software engineering framework designed to transform Natural Language (NL) requirements into fully functional, production-ready Django web applications.

By incorporating a **Structured Intermediate Representation (SIR)** engine alongside a multi-dimensional **Automated Evaluation Pipeline**, DjangoForge guarantees high syntax correctness, template rendering integrity, and dynamic domain-specific UI synthesis.

---

## ✨ Key Features

- **NL-to-SIR Extraction Engine**: Converts unstructured natural language prompts into clean JSON schemas defining models, fields, view types, and dynamic UI themes.
- **Dynamic End-to-End LLM Synthesis**: Generates full-stack Django code (Models, Views, URLs, Templates, Migrations) alongside a completely custom visual UI preview matching user prompt requirements.
- **Automated Quality Evaluation Engine**: Evaluates generated applications across 5 distinct scoring dimensions:
  - **Syntax Correctness (30%)**: AST parsing and syntax tree verification across all Python modules.
  - **Field & Model Consistency (25%)**: Cross-verification of entity field references.
  - **View Coverage (20%)**: Complete view mapping against requirements.
  - **Template Completeness (15%)**: Structural validation of base and layout templates.
  - **URL Integrity (10%)**: Dynamic routing matching and resolution verification.
- **Real-Time SSE Generation**: Built with FastAPI and Server-Sent Events (SSE) for low-latency streaming.
- **Instant Preview & ZIP Download**: Real-time visual HTML rendering with single-click `.zip` bundle export.

---

## 🏗️ System Architecture & Workflow

```text
┌───────────────────────────┐
│ Natural Language Input    │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│   SIR Extraction Engine   │  <-- Structured Intermediate Representation (JSON)
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ LLM Multi-File Synthesizer│  <-- Generates Models, Views, URLs, Templates & UI Preview
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Dynamic Evaluation Engine │  <-- Calculates AST Syntax Score & URL Integrity (OQS)
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Live Preview & ZIP Output │
└───────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Anthropic API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/DjangoForge.git
   cd DjangoForge
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   Create a `.env` file in the root directory:
   ```env
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

5. **Run the Server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

Open your browser at `http://localhost:8000` to start building applications.

---

## 📊 Evaluation Score Benchmark (OQS)

DjangoForge rates projects using an **Overall Quality Score (OQS)** formula:

$$\text{OQS} = 0.30 S_{syntax} + 0.25 S_{field} + 0.20 S_{view} + 0.15 S_{template} + 0.10 S_{url}$$

Projects scoring **≥ 90%** receive an **A Grade**, representing zero syntax errors and full functional coverage ready for deployment.

---
