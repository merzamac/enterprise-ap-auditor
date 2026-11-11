from sqlalchemy import Column, String, Numeric
from app.db.session import Base

class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"

    id = Column(String(50), primary_key=True)  
    proveedor_nombre = Column(String(150), nullable=False)
    rif_proveedor = Column(String(50), nullable=True)
    monto_aprobado = Column(Numeric(12, 2), nullable=False)
    moneda = Column(String(10), nullable=False)
    tipo_compra = Column(String(50), nullable=False)
    estado = Column(String(50), nullable=False)