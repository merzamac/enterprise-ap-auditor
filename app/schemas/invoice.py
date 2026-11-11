from typing import Optional, Literal
from pydantic import BaseModel, Field

class FacturaExtraida(BaseModel):
    orden_compra_id: Optional[str] = Field(
        default=None,
        description="Código de la orden de compra asociada (ejemplo: OC-2024-001). Si no existe, None."
    )
    proveedor_nombre: str = Field(
        description="Razón social de la empresa emisora del cobro."
    )
    rif_proveedor: Optional[str] = Field(
        default=None,
        description="Identificador fiscal o RIF de la empresa (ejemplo: J-30123456-1)."
    )
    monto_total: float = Field(
        description="Monto numérico total a pagar, sin símbolos de moneda ni separador de miles."
    )
    moneda: str = Field(
        description="Código ISO de la moneda (USD, EUR, VES)."
    )
    tipo_compra: Literal["Servicios", "Bienes", "Desconocido"] = Field(
        description="Clasificación del concepto facturado: 'Servicios', 'Bienes' o 'Desconocido'."
    )
    dias_credito: int = Field(
        default=0,
        description="Días de crédito o plazo de vencimiento indicados (0 si no se menciona)."
    )