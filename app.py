import os
import shutil
import streamlit as st
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_classic.memory import ConversationBufferMemory
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Reset vectorDb and pdfFiles on every fresh app startup
if 'app_initialized' not in st.session_state:
    for folder in ['vectorDb', 'pdfFiles']:
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)
    st.session_state.app_initialized = True

if not os.path.exists('pdfFiles'):
    os.makedirs('pdfFiles')

if not os.path.exists('vectorDb'):
    os.makedirs('vectorDb')

if 'template' not in st.session_state:
    st.session_state.template = """You are a knowledgeable chatbot, here to help with questions about the uploaded PDF documents.

    Context: {context}
    History: {history}
    
    User: {question}
    Chatbot:"""

if 'prompt' not in st.session_state:
    st.session_state.prompt = PromptTemplate(
        input_variables=["history", "context", "question"],
        template=st.session_state.template
    )

if 'memory' not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(
        memory_key="history",
        return_messages=True,
        input_key="query",
    )

if 'embeddings' not in st.session_state:
    st.session_state.embeddings = OllamaEmbeddings(
        base_url='http://localhost:11434',
        model="llama2"
    )

if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = Chroma(
        persist_directory='vectorDb',
        embedding_function=st.session_state.embeddings
    )

if 'llm' not in st.session_state:
    st.session_state.llm = OllamaLLM(
        base_url='http://localhost:11434',
        model="llama2",
        verbose=True,
    )

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Track which files have been ingested into the vectorstore this session
if 'ingested_files' not in st.session_state:
    # Check what's already in the vectorstore by looking at source metadata
    try:
        collection = st.session_state.vectorstore._collection
        if collection.count() > 0:
            existing = collection.get(include=["metadatas"])
            sources = set()
            for meta in existing.get("metadatas", []):
                if meta and "source" in meta:
                    sources.add(os.path.basename(meta["source"]))
            st.session_state.ingested_files = sources
        else:
            st.session_state.ingested_files = set()
    except Exception:
        st.session_state.ingested_files = set()


def ingest_pdf(file_path):
    """Load a PDF, split it into chunks, and add to the vectorstore."""
    file_name = os.path.basename(file_path)

    if file_name in st.session_state.ingested_files:
        return False  # Already ingested

    loader = PyPDFLoader(file_path)
    data = loader.load()

    if not data:
        st.warning(f"No text could be extracted from {file_name}")
        return False

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len
    )

    all_splits = text_splitter.split_documents(data)

    if not all_splits:
        st.warning(f"No chunks generated from {file_name}")
        return False

    # Add documents to the existing vectorstore
    st.session_state.vectorstore.add_documents(all_splits)
    st.session_state.ingested_files.add(file_name)
    return True


st.title("RAG PDF Chatbot")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["message"])

if uploaded_file is not None:
    file_path = os.path.join('pdfFiles', uploaded_file.name)

    # Save the file to disk if not already there
    if not os.path.isfile(file_path):
        bytes_data = uploaded_file.read()
        with open(file_path, 'wb') as f:
            f.write(bytes_data)

    # Ingest into vectorstore if not already ingested
    if uploaded_file.name not in st.session_state.ingested_files:
        with st.status(f"Processing {uploaded_file.name}..."):
            st.write("Loading PDF...")
            success = ingest_pdf(file_path)
            if success:
                st.write(f"✅ Ingested {uploaded_file.name} into knowledge base")
            else:
                st.write(f"⚠️ File was already in the knowledge base or could not be processed")
    else:
        st.success(f"📄 {uploaded_file.name} is ready in the knowledge base")

# Show count of documents in vectorstore
doc_count = st.session_state.vectorstore._collection.count()
if doc_count > 0:
    st.caption(f"📚 Knowledge base contains {doc_count} document chunks from {len(st.session_state.ingested_files)} file(s)")
else:
    st.info("Upload a PDF file to start asking questions about it.")

# Initialize retriever
retriever = st.session_state.vectorstore.as_retriever(
    search_kwargs={"k": 4}
)

# Handle user input
if user_input := st.chat_input("You:", key="user_input"):
    if doc_count == 0:
        st.warning("Please upload a PDF first before asking questions.")
    else:
        user_message = {"role": "user", "message": user_input}
        st.session_state.chat_history.append(user_message)

        with st.chat_message("user"):
            st.markdown(user_input)

        # Assistant response generation
        with st.chat_message("assistant"):
            message_placeholder = st.empty()

            # Get relevant context from vectorstore
            docs = retriever.invoke(user_input)
            context = "\n\n".join([doc.page_content for doc in docs])

            # Get conversation history
            memory_vars = st.session_state.memory.load_memory_variables({})
            history_str = memory_vars.get("history", "")
            if isinstance(history_str, list):
                history_str = "\n".join([f"{m.type}: {m.content}" for m in history_str])

            prompt_val = st.session_state.prompt.format(
                context=context,
                history=history_str,
                question=user_input
            )

            full_response = ""
            for chunk in st.session_state.llm.stream(prompt_val):
                full_response += chunk
                message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(full_response)

            # Save to memory
            st.session_state.memory.save_context(
                {"query": user_input}, {"output": full_response}
            )

        chatbot_message = {"role": "assistant", "message": full_response}
        st.session_state.chat_history.append(chatbot_message)
