"""Tests de las reglas de negocio del pipeline (sin BD ni LLM)."""

from app.schemas.invoice import FacturaExtraida
from app.services.agent_pipeline import evaluar_discrepancias


def factura(**kwargs) -> FacturaExtraida:
    base = {
        "proveedor_nombre": "Servicios Cloud AWS C.A.",
        "monto_total": 1000.0,
        "moneda": "USD",
        "tipo_compra": "Bienes",
    }
    base.update(kwargs)
    return FacturaExtraida(**base)


OC_OK = {
    "orden_id": "OC-2024-001",
    "proveedor_aprobado": "Servicios Cloud AWS C.A.",
    "rif_proveedor": "J-30123456-1",
    "monto_aprobado": 1000.0,
    "moneda": "USD",
    "tipo_compra": "Bienes",
    "estado": "APROBADA",
}


def contiene(alertas: list[str], texto: str) -> bool:
    return any(texto in a for a in alertas)


# 1. Factura conforme con la OC → sin alertas
assert evaluar_discrepancias(OC_OK, factura(rif_proveedor="J-30123456-1")) == []

# 2. Monto dentro de la tolerancia de 3% → sin alertas
assert (
    evaluar_discrepancias(
        OC_OK, factura(monto_total=1020.0, rif_proveedor="J-30123456-1")
    )
    == []
)

# 3. Monto fuera de tolerancia → alerta de discrepancia
assert contiene(
    evaluar_discrepancias(
        OC_OK, factura(monto_total=1100.0, rif_proveedor="J-30123456-1")
    ),
    "DISCREPANCIA DE MONTO",
)

# 4. OC cancelada → alerta aunque el monto coincida
assert contiene(
    evaluar_discrepancias(
        {**OC_OK, "estado": "CANCELADA"}, factura(rif_proveedor="J-30123456-1")
    ),
    "OC NO APROBADA",
)

# 5. Moneda distinta → alerta y no intenta comparar montos
assert contiene(
    evaluar_discrepancias(
        OC_OK, factura(moneda="VES", rif_proveedor="J-30123456-1")
    ),
    "MONEDA DISTINTA",
)

# 6. RIF distinto → alerta de proveedor distinto
assert contiene(
    evaluar_discrepancias(OC_OK, factura(rif_proveedor="J-99999999-9")),
    "PROVEEDOR DISTINTO",
)

# 7. OC con monto aprobado 0 → alerta, sin división por cero
assert contiene(
    evaluar_discrepancias(
        {**OC_OK, "monto_aprobado": 0}, factura(rif_proveedor="J-30123456-1")
    ),
    "MONTO INVÁLIDO",
)

print("OK test_validaciones: todas las reglas de negocio pasan.")
