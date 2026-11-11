import json
from app.core.llm import get_llm
from app.schemas.invoice import FacturaExtraida
from app.services.rag_engine import get_retriever
from app.services.tools import consultar_orden_compra, calcular_retenciones_fiscales


def evaluar_discrepancias(oc: dict, factura: FacturaExtraida) -> list[str]:
    """Reglas de negocio contra la OC: estado, moneda, RIF y monto (tol. 3%)."""
    alertas = []

    # La OC debe estar aprobada para poder pagar la factura
    if str(oc.get("estado", "")).upper() != "APROBADA":
        alertas.append(
            f"OC NO APROBADA: la OC '{oc.get('orden_id')}' tiene estado "
            f"'{oc.get('estado')}' y no está habilitada para pago."
        )

    # Sin moneda coincidente no tiene sentido comparar montos
    moneda_oc = str(oc.get("moneda", "")).upper()
    if moneda_oc != factura.moneda.upper():
        alertas.append(
            f"MONEDA DISTINTA: factura en {factura.moneda} vs OC en {moneda_oc}; "
            "no es posible comparar montos."
        )
    else:
        monto_aprobado = float(oc["monto_aprobado"])
        if monto_aprobado <= 0:
            alertas.append(
                f"MONTO INVÁLIDO: la OC '{oc.get('orden_id')}' tiene monto "
                f"aprobado {monto_aprobado}."
            )
        else:
            diferencia_porcentual = (
                abs(factura.monto_total - monto_aprobado) / monto_aprobado
            )
            # Regla del manual de políticas: tolerancia máxima de 3%
            if diferencia_porcentual > 0.03:
                alertas.append(
                    f"DISCREPANCIA DE MONTO: La factura es de ${factura.monto_total} "
                    f"y la Orden de Compra aprobada es de ${monto_aprobado}. "
                    f"La variación es de {diferencia_porcentual*100:.2f}%, "
                    "superando el límite permitido del 3%."
                )

    # La factura debe corresponder al proveedor aprobado en la OC (por RIF)
    rif_factura = (factura.rif_proveedor or "").replace(" ", "").upper()
    rif_oc = str(oc.get("rif_proveedor") or "").replace(" ", "").upper()
    if rif_factura and rif_oc and rif_factura != rif_oc:
        alertas.append(
            f"PROVEEDOR DISTINTO: la factura corresponde al RIF {rif_factura} "
            f"pero la OC aprobó al RIF {rif_oc}."
        )

    return alertas


def procesar_auditoria_factura(texto_factura: str) -> dict:
    llm = get_llm(temperature=0.0)

    # 1. Extracción Estructurada inicial con Pydantic
    extractor = llm.with_structured_output(FacturaExtraida)
    datos_factura: FacturaExtraida = extractor.invoke(texto_factura)

    # 2. Recuperar políticas relevantes vía RAG (pgvector)
    retriever = get_retriever()
    query_rag = f"Validación de órdenes de compra, montos y políticas de retención para tipo {datos_factura.tipo_compra}"
    documentos_politica = retriever.invoke(query_rag)

    # 3. Validar contra la Base de Datos de Órdenes de Compra (si viene un ID)
    alertas: list[str] = []
    info_oc = None

    if datos_factura.orden_compra_id:
        resultado_tool_sql = consultar_orden_compra.invoke(
            {"orden_id": datos_factura.orden_compra_id}
        )
        info_oc = resultado_tool_sql

        if "ERROR" in resultado_tool_sql:
            alertas.append(f"CRÍTICO: {resultado_tool_sql}")
        else:
            try:
                alertas.extend(
                    evaluar_discrepancias(json.loads(resultado_tool_sql), datos_factura)
                )
            except Exception as e:
                alertas.append(f"Error al validar la OC: {str(e)}")
    else:
        alertas.append(
            "FALTA DE COMPLIANCE: La factura no indica ninguna Orden de Compra asociada."
        )

    # 4. Calcular retenciones fiscales de ley
    calculo_impuestos = calcular_retenciones_fiscales.invoke(
        {
            "monto_base": datos_factura.monto_total,
            "tipo_compra": datos_factura.tipo_compra,
        }
    )

    # 5. Dictamen final consolidado
    alerta_discrepancia = " | ".join(alertas) if alertas else None
    dictamen = "RECHAZADA_POR_DISCREPANCIA" if alerta_discrepancia else "APROBADA"

    return {
        "dictamen": dictamen,
        "alerta": alerta_discrepancia,
        "datos_extraidos": datos_factura.model_dump(),
        "verificacion_oc_sql": (
            json.loads(info_oc) if info_oc and "ERROR" not in info_oc else info_oc
        ),
        "calculo_fiscal": json.loads(calculo_impuestos),
        "politicas_aplicadas_rag": [doc.page_content for doc in documentos_politica],
    }
