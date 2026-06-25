import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import json

st.set_page_config(page_title="DataCopier Cloud", layout="centered")
st.title("⚡ Buscador de Precios Centralizado")
st.write("Base de Datos: Google Cloud Firestore")

# 1. Conexión segura usando los Secrets de Streamlit
@st.cache_resource
def conectar_db():
    # Convertir las credenciales guardadas en secrets a un formato que Python entienda
    key_dict = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    return firestore.Client(credentials=creds, project=key_dict["project_id"])

db = conectar_db()

# 2. Descargar datos y guardarlos en memoria caché (Optimización de costos y velocidad)
@st.cache_data(ttl=300) # Se actualiza cada 5 minutos
def obtener_inventario():
    inventario = []
    # Consultar toda la colección
    docs = db.collection("Inventario_Precios").stream()
    for doc in docs:
        inventario.append(doc.to_dict())
    return inventario

datos = obtener_inventario()

# 3. Interfaz de Búsqueda
busqueda = st.text_input("🔍 Escribe la marca o producto:").strip().upper()

if busqueda:
    # Filtrar localmente la lista de diccionarios
    filtrados = [prod for prod in datos if busqueda in prod.get("Familia_Producto", "")]

    if filtrados:
        familias_unicas = sorted(list(set(p["Familia_Producto"] for p in filtrados)))

        if len(familias_unicas) > 1:
            familias_unicas.insert(0, "✨ ENVIAR TODAS LAS REFERENCIAS DE LA MARCA ✨")

        familia_seleccionada = st.selectbox("📋 Selecciona la opción requerida:", familias_unicas)

        if familia_seleccionada:
            texto_whatsapp = ""

            if familia_seleccionada == "✨ ENVIAR TODAS LAS REFERENCIAS DE LA MARCA ✨":
                texto_whatsapp = f"🏪 *PORTAFOLIO: {busqueda}* 🏪\n\n"
                # Iterar sobre las familias originales (sin incluir la opción "TODAS")
                for fam in familias_unicas[1:]:
                    sub_bloque = [p for p in filtrados if p["Familia_Producto"] == fam]
                    texto_whatsapp += f"🔹 *{fam}*\n"
                    for prod in sub_bloque:
                        precio = f"${prod['Precio']:,}".replace(",", ".")
                        texto_whatsapp += f"  • {prod['Presentacion']}  ➡️  {precio}\n"
                    texto_whatsapp += "\n"
                texto_whatsapp += "¿Cuál de estas opciones preparamos para tu despacho?"
                
            else:
                bloque_individual = [p for p in filtrados if p["Familia_Producto"] == familia_seleccionada]
                texto_whatsapp = f"🍼 *{familia_seleccionada}* 🍼\n\n"
                for prod in bloque_individual:
                    precio = f"${prod['Precio']:,}".replace(",", ".")
                    texto_whatsapp += f"• {prod['Presentacion']}  ➡️  {precio}\n"
                texto_whatsapp += "\n¿Te gustaría que agendemos alguna de estas presentaciones?"

            st.write("### Copia este bloque para WhatsApp:")
            st.code(texto_whatsapp, language="text")
    else:
        st.warning("No se encontraron coincidencias en el inventario.")