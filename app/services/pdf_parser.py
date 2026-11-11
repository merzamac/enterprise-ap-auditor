from langchain_community.document_loaders import PyPDFLoader


def extraer_texto_de_pdf(ruta_archivo_pdf: str) -> str:
    """
    Lee un archivo PDF local y concatena el texto de todas sus páginas
    en un solo string limpio para que la IA lo procese.
    """
    try:
        loader = PyPDFLoader(ruta_archivo_pdf)
        paginas = loader.load()

        # Unir el texto de todas las páginas del PDF
        texto_completo = "\n".join([page.page_content for page in paginas])
        return texto_completo
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo PDF: {str(e)}")
