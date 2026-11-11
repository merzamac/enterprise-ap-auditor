from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def crear_pdf(nombre_archivo, contenido):
    Path("test_pdfs").mkdir(exist_ok=True)
    ruta = Path("test_pdfs") / nombre_archivo

    # reportlab exige str, no Path
    c = canvas.Canvas(str(ruta), pagesize=letter)
    width, height = letter

    # Escribir el texto línea por línea en el PDF
    y = height - 50
    for linea in contenido.split("\n"):
        c.drawString(50, y, linea)
        y -= 20

    c.save()
    print(f"📄 Creado PDF de prueba: {ruta}")


# Factura 1: Coincide perfecto con la OC-2024-001 ($1,200)
factura_1 = """
FACTURA COMERCIAL #1029
Proveedor: Servicios Cloud AWS C.A.
RIF: J-30123456-1
Fecha: 2026-03-30
Orden de Compra Asociada: OC-2024-001

Concepto: Consultoría y servidores del mes en curso.
Subtotal: $1,200.00 USD
Condiciones de Pago: 30 días.
"""

# Factura 2: Discrepancia de monto (La OC-2024-002 era por $450, aquí cobran $650)
factura_2 = """
FACTURA COMERCIAL #4059
Proveedor: Hardware & Redes Global
RIF: J-40987654-2
Fecha: 2026-03-30
Orden de Compra Asociada: OC-2024-002

Concepto: Compra de switches y cables UTP.
Monto Total: $650.00 USD (Incluye flete de emergencia)
Condiciones de Pago: Contado.
"""

# Factura 3: Sin Orden de Compra (Debe requerir auditoría manual)
factura_3 = """
NOTA DE ENTREGA / COBRO #8881
Proveedor: Agencia Creativa X
RIF: J-99999999-9
Fecha: 2026-03-30
Orden de Compra: N/A

Concepto: Campaña de marketing digital en redes sociales.
Monto Total: $2,500.00 USD
"""

if __name__ == "__main__":
    crear_pdf("factura_valida.pdf", factura_1)
    crear_pdf("factura_discrepancia.pdf", factura_2)
    crear_pdf("factura_sin_oc.pdf", factura_3)
    print("\n¡Todos los PDFs de prueba han sido generados en la carpeta /test_pdfs/!")
