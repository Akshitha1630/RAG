# 📄 RAG PDF Chatbot

A **Retrieval-Augmented Generation (RAG)** chatbot built with **Streamlit**, **LangChain**, and **Ollama** that lets you upload PDF documents and ask questions about their content using a locally-hosted LLM.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.57+-red?logo=streamlit)
![LangChain](https://img.shields.io/badge/LangChain-1.3+-green)
![Ollama](https://img.shields.io/badge/Ollama-Llama2-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Web UI                        │
│                    (Upload PDF + Chat Interface)                │
└──────────────┬────────────────────────────┬─────────────────────┘
               │                            │
         PDF Upload                   User Question
               │                            │
               ▼                            ▼
┌──────────────────────┐       ┌──────────────────────────┐
│   Document Ingestion │       │   Retrieval Pipeline     │
│                      │       │                          │
│  1. PyPDFLoader      │       │  1. Embed user query     │
│  2. Text Splitter    │       │  2. Similarity search    │
│  3. Embed chunks     │       │  3. Retrieve top-k docs  │
│  4. Store in ChromaDB│       │  4. Build prompt         │
└──────────┬───────────┘       └────────────┬─────────────┘
           │                                │
           ▼                                ▼
┌──────────────────────┐       ┌──────────────────────────┐
│   ChromaDB Vector    │◄──────│   Ollama LLM (Llama2)   │
│      Store           │       │                          │
│  (Persistent on disk)│       │  Generates response      │
└──────────────────────┘       │  using context + history │
                               └──────────────────────────┘
```

---

## 🔍 How It Works

### 1. Document Ingestion Pipeline

When a user uploads a PDF through the Streamlit interface:

1. **PDF Loading** — `PyPDFLoader` reads the PDF and extracts raw text from each page.
2. **Text Splitting** — `RecursiveCharacterTextSplitter` breaks the text into manageable chunks (1500 characters with 200-character overlap) to fit within the LLM's context window while preserving semantic coherence.
3. **Embedding Generation** — Each chunk is converted into a high-dimensional vector embedding using the `Llama2` model via Ollama's embedding API.
4. **Vector Storage** — Embeddings are stored in a **ChromaDB** vector database persisted to disk (`vectorDb/`), enabling fast similarity search across sessions.

### 2. Retrieval-Augmented Generation (RAG)

When a user asks a question:

1. **Query Embedding** — The user's question is embedded into the same vector space as the document chunks.
2. **Similarity Search** — ChromaDB performs a cosine similarity search to find the **top 4 most relevant** document chunks.
3. **Context Assembly** — The retrieved chunks are concatenated to form the context window.
4. **Prompt Construction** — A prompt is built combining:
   - The retrieved **context** (relevant document chunks)
   - The **conversation history** (for multi-turn coherence)
   - The user's **question**
5. **LLM Generation** — The prompt is sent to the **Llama2** model running locally via Ollama, which generates a contextually grounded response.
6. **Streaming Output** — The response is streamed token-by-token to the UI for a real-time chat experience.

### 3. Conversation Memory

The chatbot maintains a `ConversationBufferMemory` that stores the full history of user-assistant exchanges. This enables:
- Follow-up questions that reference previous answers
- Contextual continuity across multiple turns
- A natural conversational flow

---

## 📁 Project Structure

```
RAG/
├── app.py                  # Main Streamlit application
├── generate_docs.py        # Script to generate Word documentation
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── .gitignore              # Git ignore rules
├── docs/
│   └── RAG_PDF_Chatbot_Documentation.docx  # Generated Word documentation
├── pdfFiles/               # Uploaded PDFs (git-ignored)
│   └── (user-uploaded PDFs stored here)
└── vectorDb/               # ChromaDB persistent storage (git-ignored)
    └── (vector embeddings stored here)
```

---

## 🛠️ Tech Stack

| Component         | Technology                   | Purpose                                    |
|--------------------|------------------------------|--------------------------------------------|
| **Frontend**       | Streamlit                    | Web UI for file upload and chat            |
| **LLM**            | Ollama (Llama2)              | Local language model for text generation   |
| **Embeddings**     | Ollama (Llama2)              | Vector embeddings for semantic search      |
| **Vector Store**   | ChromaDB                     | Persistent vector database                 |
| **Framework**      | LangChain                    | Orchestration of RAG pipeline              |
| **PDF Parsing**    | PyPDF                        | PDF text extraction                        |
| **Memory**         | LangChain ConversationBuffer | Multi-turn conversation history            |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Conda** (package manager)
- **Ollama** installed and running locally

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/RAG-PDF-Chatbot.git
cd RAG-PDF-Chatbot
```

### 2. Set Up the Conda Environment

```bash
conda create -n rag_env python=3.10 -y
conda activate rag_env
pip install -r requirements.txt
```

### 3. Install and Start Ollama

Download Ollama from [ollama.com](https://ollama.com/) and install it. Then pull the Llama2 model:

```bash
ollama pull llama2
```

Ensure Ollama is running (it runs as a background service by default on port `11434`):

```bash
ollama serve
```

### 4. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## 💬 Usage

1. **Upload a PDF** — Click the "Upload a PDF file" button and select any PDF document.
2. **Wait for Processing** — The app will extract text, generate embeddings, and store them. You'll see a progress indicator.
3. **Ask Questions** — Type your question in the chat input at the bottom of the page.
4. **Get Answers** — The chatbot will retrieve relevant sections from your PDF and generate an informed response.
5. **Follow Up** — Ask follow-up questions; the chatbot remembers conversation context.

---

## ⚙️ Configuration

| Parameter           | Default               | Description                                    |
|----------------------|-----------------------|------------------------------------------------|
| `base_url`          | `http://localhost:11434` | Ollama server URL                            |
| `model`             | `llama2`              | LLM model name                                |
| `chunk_size`        | `1500`                | Characters per text chunk                      |
| `chunk_overlap`     | `200`                 | Overlap between consecutive chunks             |
| `search_kwargs.k`   | `4`                   | Number of retrieved document chunks per query  |

To change models (e.g., use `mistral` or `llama3`), update the `model` parameter in `app.py` for both `OllamaEmbeddings` and `OllamaLLM`.

---

## 🧪 Generating Documentation

To regenerate the Word documentation:

```bash
python generate_docs.py
```

This creates `docs/RAG_PDF_Chatbot_Documentation.docx` with full system documentation.

---

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📧 Contact

Feel free to reach out via GitHub Issues.
