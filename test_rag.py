from app.services.rag_engine import inicializar_vector_store, get_retriever


def probar_rag():
    print("--- 1. Inicializando y vectorizando documentos en PostgreSQL ---")
    inicializar_vector_store()

    print("\n--- 2. Probando Búsqueda Semántica (Retriever) ---")
    retriever = get_retriever()

    pregunta = (
        "¿Cuál es la tolerancia máxima de variación en el monto de una orden de compra?"
    )
    print(f"Consulta: '{pregunta}'\n")

    documentos_encontrados = retriever.invoke(pregunta)

    for i, doc in enumerate(documentos_encontrados, 1):
        print(f"Resultado #{i} (Fragmento relevante):")
        print(doc.page_content)
        print("-" * 40)


if __name__ == "__main__":
    probar_rag()
