import json
from langchain_core.tools import tool
from app.db.session import SessionLocal
from app.db.models import OrdenCompra


@tool
def consultar_orden_compra(orden_id: str) -> str:
    """
    Consulta en la base de datos PostgreSQL los detalles de una Orden de Compra (OC).
    Útil para verificar si una OC existe, su monto aprobado, proveedor autorizado y estado.
    """
    db = SessionLocal()
    try:
        orden = db.query(OrdenCompra).filter(OrdenCompra.id == orden_id.strip()).first()
        if not orden:
            return f"ERROR: La orden de compra '{orden_id}' no existe en el sistema."

        resultado = {
            "orden_id": orden.id,
            "proveedor_aprobado": orden.proveedor_nombre,
            "rif_proveedor": orden.rif_proveedor,
            "monto_aprobado": float(orden.monto_aprobado),
            "moneda": orden.moneda,
            "tipo_compra": orden.tipo_compra,
            "estado": orden.estado,
        }
        return json.dumps(resultado, ensure_ascii=False)
    except Exception as e:
        return f"ERROR al consultar la base de datos: {str(e)}"
    finally:
        db.close()


@tool
def calcular_retenciones_fiscales(monto_base: float, tipo_compra: str) -> str:
    """
    Calcula de forma exacta las retenciones fiscales de ley (IVA e ISLR) sobre un monto base.
    Aplica 16% de IVA, retención del 75% del IVA y 5% de ISLR solo si es tipo 'Servicios'.
    """
    tasa_iva = 0.16
    tasa_retencion_iva = 0.75  # 75% del IVA facturado
    tasa_islr = 0.05 if tipo_compra.lower() == "servicios" else 0.0  # 5% si es servicio

    monto_iva = round(monto_base * tasa_iva, 2)
    monto_total_con_iva = round(monto_base + monto_iva, 2)

    retencion_iva = round(monto_iva * tasa_retencion_iva, 2)
    retencion_islr = round(monto_base * tasa_islr, 2)
    total_retenido = round(retencion_iva + retencion_islr, 2)

    monto_neto_a_pagar = round(monto_total_con_iva - total_retenido, 2)

    resultado = {
        "monto_base": monto_base,
        "monto_iva_16": monto_iva,
        "monto_total_bruto": monto_total_con_iva,
        "retencion_iva_75": retencion_iva,
        "retencion_islr_5": retencion_islr,
        "total_retenido": total_retenido,
        "monto_neto_a_pagar": monto_neto_a_pagar,
    }
    return json.dumps(resultado, ensure_ascii=False)


# Lista exportable de herramientas disponibles para el agente
herramientas_contables = [consultar_orden_compra, calcular_retenciones_fiscales]
