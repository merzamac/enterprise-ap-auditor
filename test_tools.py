from app.core.llm import get_llm
from app.services.tools import herramientas_contables, consultar_orden_compra

# 1. Obtenemos el LLM y le vinculamos las herramientas
llm = get_llm(temperature=0.0)
llm_con_tools = llm.bind_tools(herramientas_contables)

# 2. Le hacemos una pregunta que requiere consultar la BD
pregunta = "Necesito saber si la orden OC-2024-001 está aprobada y cuál es su monto."
print(f"Pregunta del usuario: {pregunta}\n")

respuesta = llm_con_tools.invoke(pregunta)

# 3. Comprobamos la decisión del modelo
if respuesta.tool_calls:
    llamada = respuesta.tool_calls[0]
    print(f"✅ El modelo decidió invocar la herramienta: '{llamada['name']}'")
    print(f"Argumentos extraídos por el LLM: {llamada['args']}\n")

    # Ejecutamos la herramienta real en PostgreSQL
    resultado_bd = consultar_orden_compra.invoke(llamada["args"])
    print(f"📦 Resultado directo desde PostgreSQL:\n{resultado_bd}")
else:
    print(f"El modelo respondió texto directo: {respuesta.content}")
