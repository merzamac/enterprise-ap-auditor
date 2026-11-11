from pathlib import Path
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from app.services.agent_pipeline import procesar_auditoria_factura
from app.services.pdf_parser import extraer_texto_de_pdf
from app.services.rag_engine import inicializar_vector_store

app = FastAPI(
    title="Enterprise AP & Fiscal Audit Copilot",
    version="1.0.0",
    description="Backend de auditoría y cuentas por pagar basado en LangChain, pgvector y FastAPI.",
)


@app.on_event("startup")
def startup_event():
    try:
        inicializar_vector_store()
    except Exception as e:
        print(f"Aviso en startup de vector store: {e}")


@app.get("/")
def read_root():
    return {"status": "online", "service": "AP Audit Copilot API is running."}


@app.post("/api/v1/auditar-factura-pdf")
def auditar_factura_pdf(file: UploadFile = File(...)):
    """
    Recibe una factura en formato PDF, extrae su texto mediante PyPDFLoader,
    ejecuta el pipeline de RAG, validación SQL y cálculo fiscal.
    """
    # Path().name descarta cualquier ruta enviada por el cliente (path traversal)
    filename = Path(file.filename or "").name
    if not filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="El archivo enviado debe ser obligatoriamente un PDF.",
        )

    # Guardar temporalmente el PDF subido en disco
    temp_dir = Path("temp_pdfs")
    temp_dir.mkdir(exist_ok=True)
    temp_file_path = temp_dir / filename

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. Extraer texto del PDF usando LangChain PyPDFLoader
        texto_factura = extraer_texto_de_pdf(temp_file_path)

        if not texto_factura.strip():
            raise HTTPException(
                status_code=400,
                detail="El PDF parece estar vacío o es una imagen escaneada sin capa de texto.",
            )

        # 2. Ejecutar el pipeline de auditoría que ya construimos
        resultado = procesar_auditoria_factura(texto_factura)

        return {
            "success": True,
            "archivo_procesado": filename,
            "resultado_auditoria": resultado,
        }

    except HTTPException:
        # Los errores de validación (400) no deben reenvolverse como 500
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error procesando el PDF: {str(e)}"
        )

    finally:
        # Limpiar y borrar el archivo temporal del disco
        temp_file_path.unlink(missing_ok=True)
