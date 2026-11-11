# Enterprise AP & Fiscal Audit Copilot

Backend inteligente de auditoría de **cuentas por pagar**: recibe facturas en PDF, las convierte en datos estructurados con IA, las valida contra las órdenes de compra aprobadas y las políticas internas de la empresa, y devuelve un dictamen de pago — **APROBADA** o **RECHAZADA** — con el cálculo de retenciones fiscales incluido.

Construido con **FastAPI**, **LangChain**, **Gemini** y **PostgreSQL + pgvector**.

---

## Problemática

En cualquier empresa que paga a proveedores:

1. **Se pagan facturas sin verificarlas.** Nada garantiza que el monto facturado coincida con la Orden de Compra (OC) aprobada, que el proveedor sea el autorizado o que la OC siga vigente → fraudes, pagos excesivos y pagos a proveedores no autorizados.
2. **Las políticas están en documentos muertos.** La tolerancia del 3%, las retenciones fiscales y los umbrales de aprobación viven en un manual que nadie consulta en el momento de pagar.
3. **Las facturas llegan como PDF.** Texto no estructurado: no se puede validar automáticamente contra el sistema.
4. **La revisión manual es lenta e inconsistente.** Un auditor dedicado tarda minutos por factura y su criterio varía.

## La solución

Un pipeline que automatiza la auditoría completa de cada factura:

```
┌─────────────┐   ┌───────────────┐   ┌──────────────────────────┐
│ PDF factura │──▶│ PyPDFLoader   │──▶│ Gemini + Pydantic        │
└─────────────┘   │ texto plano   │   │ extracción estructurada  │
                  └───────────────┘   └────────────┬─────────────┘
                                                   │ FacturaExtraida
              ┌────────────────────────────────────┼───────────────────────────┐
              ▼                                    ▼                           ▼
   ┌────────────────────┐              ┌────────────────────┐      ┌─────────────────────┐
   │ RAG con pgvector   │              │ SQL: OC en         │      │ Cálculo fiscal      │
   │ políticas relevant │              │ PostgreSQL         │      │ IVA · ISLR          │
   └─────────┬──────────┘              └─────────┬──────────┘      └──────────┬──────────┘
             └──────────────────┬────────────────┘                           │
                                ▼                                            │
                  ┌─────────────────────────────────┐                        │
                  │ Reglas de negocio               │◀───────────────────────┘
                  │ estado · moneda · RIF · tol. 3% │
                  └────────────────┬────────────────┘
                                   ▼
              APROBADA  |  RECHAZADA_POR_DISCREPANCIA
```

| Paso | Qué hace |
|---|---|
| 1. Subida | `POST` multipart con el PDF de la factura |
| 2. Extracción de texto | `PyPDFLoader` une el texto de todas las páginas |
| 3. Extracción estructurada | Gemini con `with_structured_output(FacturaExtraida)` devuelve OC, proveedor, RIF, monto, moneda y tipo de compra validados por Pydantic |
| 4. RAG | Los fragmentos de `docs/politicas_empresa.md` vectorizados con `gemini-embedding-001` recuperan las políticas aplicables al tipo de compra |
| 5. Validación SQL | La tool `consultar_orden_compra` consulta la OC en PostgreSQL |
| 6. Reglas de negocio | Estado de la OC, coincidencia de moneda y RIF, y tolerancia del 3% sobre el monto |
| 7. Cálculo fiscal | IVA 16%, retención del 75% del IVA e ISLR 5% en servicios |
| 8. Dictamen | Consolida alertas en una respuesta única |

## Conceptos implementados

| Concepto | Dónde se aplica |
|---|---|
| **FastAPI** | API REST, subida de archivos multipart, manejo de errores HTTP |
| **LangChain** | Orquestación del LLM: `with_structured_output` y tools con `@tool` |
| **RAG (Retrieval-Augmented Generation)** | `pgvector` + embeddings de Gemini para recuperar políticas de la empresa |
| **Pydantic v2** | Esquema `FacturaExtraida`: la extracción del LLM llega tipada y validada |
| **SQLAlchemy 2.0** | ORM contra PostgreSQL (tabla `ordenes_compra`) |
| **Gemini (Google GenAI)** | Modelo `gemini-3.5-flash-lite` para extracción y `gemini-embedding-001` para vectores |
| **Docker** | Base `pgvector/pgvector:pg16` con `docker compose` |
| **Tests** | `test_validaciones.py`: 7 asserts sobre las reglas de negocio, sin BD ni LLM |

## Cómo llegamos a la solución

La primera versión "funcionaba", pero una auditoría del propio sistema encontró que **aprobaba facturas que debía rechazar**. Esto es lo que se corrigió y cómo se verificó:

1. **La detección de discrepancias era código muerto.** El chequeo de errores hacía `.lower()` sobre un `dict` → `AttributeError` silenciado por un `except: pass`. Ninguna factura se rechazaba jamás por monto. → Se valida el string de la tool *antes* de parsearlo.
2. **`NameError` cuando la factura no traía OC.** `import json` estaba dentro de un `if`, pero la respuesta final siempre necesita `json`. → `import` a nivel de módulo.
3. **Chunks duplicados en cada arranque.** `add_documents` sin limpiar repetía las políticas con cada restart y contaminaba el retrieval. → `delete_collection()` + `create_collection()` antes de indexar — verificado: **4 chunks tras 2 reinicios**.
4. **Path traversal en la subida.** El nombre de archivo venía del cliente y podía sobrescribir y borrar archivos fuera de `temp_pdfs`. → `Path(file.filename).name`.
5. **Errores 400 que llegaban como 500.** El `except Exception` engullía las `HTTPException` de validación. → `except HTTPException: raise`.
6. **API congelada por un solo request.** El endpoint era `async def` pero ejecutaba LLM, SQL y PDF de forma bloqueante en el event loop. → `def` (FastAPI lo ejecuta en threadpool).
7. **Validaciones incompletas.** Solo se comparaban montos. → `evaluar_discrepancias()`: estado de la OC, moneda, RIF del proveedor y monto aprobado ≤ 0.
8. **Verificación end-to-end.** Los 3 escenarios de prueba ejecutados contra Gemini + PostgreSQL reales, y `test_validaciones.py` con asserts de las reglas de negocio.

## Estructura del proyecto

```
enterprise-ap-auditor/
├── app/
│   ├── main.py                  # API FastAPI (endpoint de auditoría PDF)
│   ├── core/
│   │   ├── config.py            # Settings desde .env (pydantic-settings)
│   │   └── llm.py               # Factory del modelo Gemini
│   ├── db/
│   │   ├── models.py            # OrdenCompra (SQLAlchemy)
│   │   └── session.py           # Engine y sesiones de BD
│   ├── schemas/
│   │   └── invoice.py           # FacturaExtraida (Pydantic)
│   └── services/
│       ├── agent_pipeline.py    # Orquestador de la auditoría
│       ├── pdf_parser.py        # Extracción de texto desde PDF
│       ├── rag_engine.py        # Vector store pgvector + retriever
│       └── tools.py             # Tools: consulta de OC y retenciones
├── docs/
│   └── politicas_empresa.md     # Manual de políticas (fuente del RAG)
├── test_pdfs/                   # Facturas de prueba (generadas)
├── generar_pdfs.py              # Generador de fixtures PDF
├── seed.py                      # Esquema de BD + órdenes de compra de prueba
├── test_validaciones.py         # Tests de las reglas de negocio
├── docker-compose.yml           # PostgreSQL + pgvector
└── pyproject.toml               # Dependencias (PDM)
```

## Puesta en marcha

```bash
# 1. Base de datos
docker compose up -d

# 2. Dependencias
pdm install

# 3. Clave de Gemini en .env
cp .env.example .env             # editar GOOGLE_API_KEY

# 4. Datos de prueba
python seed.py
python generar_pdfs.py           # crea los 3 PDFs en test_pdfs/

# 5. Arrancar
uvicorn app.main:app --reload
```

> **Windows:** usar una consola UTF-8 (`$env:PYTHONUTF8="1"`) para evitar `UnicodeEncodeError` en los `print` con emojis.

## API

### `POST /api/v1/auditar-factura-pdf`

```bash
curl -F "file=@test_pdfs/factura_discrepancia.pdf" \
  http://localhost:8000/api/v1/auditar-factura-pdf
```

Respuesta real (extracto):

```json
{
  "success": true,
  "archivo_procesado": "factura_discrepancia.pdf",
  "resultado_auditoria": {
    "dictamen": "RECHAZADA_POR_DISCREPANCIA",
    "alerta": "DISCREPANCIA DE MONTO: La factura es de $650.0 y la Orden de Compra aprobada es de $450.0. La variación es de 44.44%, superando el límite permitido del 3%.",
    "datos_extraidos": {
      "orden_compra_id": "OC-2024-002",
      "proveedor_nombre": "Hardware & Redes Global",
      "rif_proveedor": "J-40987654-2",
      "monto_total": 650.0,
      "moneda": "USD",
      "tipo_compra": "Bienes",
      "dias_credito": 0
    },
    "verificacion_oc_sql": {
      "orden_id": "OC-2024-002",
      "monto_aprobado": 450.0,
      "estado": "APROBADA"
    },
    "calculo_fiscal": {
      "monto_base": 650.0,
      "monto_iva_16": 104.0,
      "retencion_iva_75": 78.0,
      "retencion_islr_5": 0.0,
      "total_retenido": 78.0,
      "monto_neto_a_pagar": 676.0
    },
    "politicas_aplicadas_rag": ["...fragmentos de políticas recuperados por RAG..."]
  }
}
```

También está disponible `GET /` como healthcheck.

### Escenarios de prueba incluidos

| PDF | Escenario | Dictamen |
|---|---|---|
| `factura_valida.pdf` | OC-2024-001 por $1.200, monto exacto | `APROBADA` |
| `factura_discrepancia.pdf` | $650 facturados contra OC de $450 (+44,44%) | `RECHAZADA_POR_DISCREPANCIA` |
| `factura_sin_oc.pdf` | Factura sin orden de compra asociada | `RECHAZADA_POR_DISCREPANCIA` |

## Roadmap

- [ ] Umbrales de autorización del manual ($500 / $3.000)
- [ ] Regla de vencimiento (< 15 días desde emisión)
- [ ] Exención de retención para "Agente Especial"
- [ ] Conversión de moneda antes de comparar montos
- [ ] Autenticación en la API
- [ ] Migrar `on_event("startup")` al lifespan de FastAPI

---

**Autor:** Moises Merza · **Licencia:** MIT
