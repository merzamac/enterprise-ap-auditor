from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from app.core.config import settings


def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=settings.GOOGLE_API_KEY,
    )


def get_vector_store():
    embeddings = get_embeddings()
    return PGVector(
        embeddings=embeddings,
        collection_name="politicas_empresa_vector",
        connection=settings.database_url,
        use_jsonb=True,
    )


def inicializar_vector_store():
    vector_store = get_vector_store()

    ruta_docs = Path(__file__).resolve().parents[2] / "docs" / "politicas_empresa.md"

    if not ruta_docs.exists():
        print(f"⚠️ No se encontró el archivo de políticas en: {ruta_docs}")
        return

    with open(ruta_docs, "r", encoding="utf-8") as f:
        texto_markdown = f.read()

    doc = Document(
        page_content=texto_markdown, metadata={"source": "politicas_empresa.md"}
    )

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents([doc])

    # Recrea la colección en cada arranque: sin esto, cada restart duplica los chunks
    vector_store.delete_collection()
    vector_store.create_collection()
    vector_store.add_documents(chunks)
    print(
        f"✅ RAG inicializado: {len(chunks)} fragmentos vectorizados con `gemini-embedding-001` y guardados en PostgreSQL."
    )


def get_retriever():
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_kwargs={"k": 2})
