# 🔍 ContextLens

<p align="center">
  <img src="https://img.shields.io/badge/MCP-v2.0.0-blue?style=for-the-badge&logo=anthropic" alt="MCP v2">
  <img src="https://img.shields.io/badge/Language-Python_3.11+-green?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Database-LanceDB-orange?style=for-the-badge&logo=lancedb" alt="LanceDB">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT License">
</p>

---

### **The "Zero-API" Knowledge Bridge for AI Agents**

**ContextLens** is an open-source, local-first background daemon and Model Context Protocol (MCP) server. It bridges the "context gap" by turning non-API desktop applications—like **Apple Notes**, **UpNote**, **Legacy ERPs**, and **Slack/Teams huddles**—into queryable, semantic knowledge bases for your AI agents.

> "If you can see it on your screen, your AI agent can now reason about it." 🦞

---

## ✨ Key Features

### 🚀 **Advanced Extraction**
*   **OS Accessibility Scraping**: High-fidelity text extraction using native macOS/Windows accessibility trees.
*   **Firecrawl-style Markdown**: Transforms messy UI layouts into clean, semantic Markdown perfectly optimized for LLMs.
*   **Local OCR Fallback**: Integrated Tesseract/EasyOCR for applications that hide text behind custom canvases.

### 🧠 **Intelligent Memory (Local RAG)**
*   **Continuous Indexing**: A silent background watcher that maps your workspace in real-time.
*   **Vector Search (LanceDB)**: Blazing fast semantic retrieval using local `all-MiniLM-L6-v2` embeddings.
*   **Privacy First**: 100% local. Your data, your screen, your embeddings—nothing ever leaves your machine.

### 🔌 **Modern MCP v2 Support**
*   **URI Resources**: Passive context injection via `contextlens://apps/{app}/latest`.
*   **Async Tasks (SEP-1686)**: Long-running "Deep Index" jobs for entire apps with status polling.
*   **Elicitation (SEP-382)**: Secure "Human-in-the-Loop" confirmation for destructive actions.
*   **Server Cards**: Automatic discovery for modern AI clients (Claude Desktop, Cursor, Zed).

---

## 🛠 How it Works

```mermaid
graph LR
    A[Desktop App] -->|Accessibility/OCR| B(ContextLens Extractor)
    B --> C{Content Hash}
    C -->|New| D[Local Vector DB]
    C -->|Duplicate| E[Skip]
    D --> F[LanceDB]
    F -->|MCP v2| G[AI Agent: Claude/Cursor]
```

---

## 🏗️ Architecture Deep Dive

ContextLens is not a simple screen scraper; it is a continuous, local-first semantic indexing pipeline. Here’s exactly what happens under the hood every 30 seconds:

### 1. Extraction Layer (`extractor.py`)
- **macOS Deep Trees:** We bypass simple OCR by default. Our AppleScript engine recursively unwraps the entire `NSAccessibility` tree, converting nested UI elements (Groups, Tables, SplitViews) into flat, ordered text. This preserves the spatial relationship of UI elements.
- **Firecrawl-Style Markdown:** The raw UI text is transformed into clean, LLM-optimized Markdown via heuristics that detect headers vs. content based on line length.
- **Fallback Cascade:** If the Accessibility tree is empty (e.g., canvas apps, Citrix), we automatically fall back to local Tesseract OCR.

### 2. Chunking & Embedding Strategy (`indexer.py`)
We prioritize **contextual contiguity** over naive recursive splitting:
- **Semantic-Aware Chunking:** We don't split on arbitrary character counts. The engine first splits on `\n\n` (paragraph boundaries) and only breaks when a chunk exceeds **500 characters**. This keeps reasoning steps intact.
- **Overlap Strategy:** Currently, we use discrete chunks. *(Planned: Adding a 50-character sliding window overlap between chunks to prevent retrieval fragmentation).*
- **Embedding Model:** We default to `all-MiniLM-L6-v2` (384 dimensions) via `sentence-transformers`. It runs **entirely on CPU**, generating vectors in sub-10ms.
- **Storage:** Vectors are stored in **LanceDB** (v0.30+), a columnar vector database built on Apache Arrow. This gives our index zero-copy interoperability with the PyData ecosystem (Pandas, Polars, PyArrow).

### 3. Deduplication Logic (`watcher.py`)
We maintain an **MD5 hash map** of the last indexed screen state. If a window hasn't changed, we skip embedding entirely, saving precious context window bandwidth.

---

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.11+
*   **macOS**: Native support.
*   **Windows**: Native UIAutomation support.
*   **OCR (Optional)**:
    ```bash
    brew install tesseract
    ```

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-username/contextlens.git
cd contextlens

# Install dependencies with uv
uv sync
```

### 3. Running the Server
```bash
# Start the daemon and MCP gateway
uv run python -m src.contextlens.main
```

---

## 🔌 Connecting to AI Agents

### **Claude Desktop**
Add the following to your `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "contextlens": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/contextlens",
        "run",
        "python",
        "-m",
        "src.contextlens.main"
      ]
    }
  }
}
```

### **Cursor / Zed**
Simply point the MCP server configuration to the same `uv` command. The **Server Card** at `contextlens://.well-known/mcp-server-card.json` will help the editor discover all available tools automatically.

---

## 🛡 Security & Ethics
*   **Audit Logs**: Every tool call and extraction is logged locally.
*   **Schema Safety**: Strict Pydantic validation on all agent inputs.
*   **Elicitation**: Destructive actions (like clearing the index) *require* explicit user confirmation.

---

## 🤝 Contributing
We love contributors! If you want to build a better bridge for AI agents, check out our [Contribution Guide](CONTRIBUTING.md).

## 📄 License
MIT © 2026-2027 ContextLens Team
