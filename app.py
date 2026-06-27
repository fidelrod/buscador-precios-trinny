import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account
import json
import re

# Configuración de página
st.set_page_config(page_title="Precios Trinny", layout="centered")
st.title("Buscador de Precios - Trinny")

# --- Función para limpiar palabras de empaque ---
def limpiar_presentacion(texto):
    palabras_a_eliminar = ["tarro", "caja", "frasco", "sobre", "ampolla", "und", "unidades"]
    patron = r'\b(' + '|'.join(palabras_a_eliminar) + r')\b'
    limpio = re.sub(patron, '', texto, flags=re.IGNORECASE).strip()
    return limpio

# 1. Conexión a Firestore (Caché a nivel de recurso: solo se conecta una vez por sesión del servidor)
@st.cache_resource
def conectar_db():
    key_dict = json.loads(st.secrets["textkey"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    return firestore.Client(credentials=creds)

# 2. Cargar datos una sola vez (Caché global)
@st.cache_resource
def obtener_inventario():
    db = conectar_db()
    inventario = []
    # Usamos stream para no bloquear la memoria al cargar
    docs = db.collection("Inventario_Precios").stream()
    for doc in docs:
        inventario.append(doc.to_dict())
    return inventario

# Esto carga los datos solo la primera vez que inicia la app
with st.spinner('Cargando inventario desde la nube...'):
    datos = obtener_inventario()

# 3. Interfaz de búsqueda
busqueda = st.text_input("Escribe la marca o producto:").strip().upper()

if busqueda:
    # Filtrar datos que ya están en memoria (RAM), no en Firestore
    filtrados = [prod for prod in datos if busqueda in prod.get("Familia_Producto", "").upper()]

    if filtrados:
        familias = sorted(list(set(p["Familia_Producto"] for p in filtrados)))
        
        if len(familias) > 1:
            familias.insert(0, "ENVIAR TODAS LAS REFERENCIAS")
            
        seleccion = st.selectbox("Selecciona la referencia:", familias)

        if seleccion:
            texto = ""
            if seleccion == "ENVIAR TODAS LAS REFERENCIAS":
                texto = f"*Portafolio: {busqueda.capitalize()}*\n\n"
                for fam in familias[1:]:
                    texto += f"*{fam.title()}*\n"
                    for p in [p for p in filtrados if p["Familia_Producto"] == fam]:
                        presentacion_limpia = limpiar_presentacion(p['Presentacion'])
                        precio = f"${p['Precio']:,}".replace(",", ".")
                        texto += f"• {presentacion_limpia}  ->  {precio}\n"
                    texto += "\n"
                texto += "¿Cuál de estas opciones preparamos para tu despacho?"
            else:
                bloque = [p for p in filtrados if p["Familia_Producto"] == seleccion]
                encabezado = seleccion.title()
                texto = f"*{encabezado}*\n\n"
                for p in bloque:
                    presentacion_limpia = limpiar_presentacion(p['Presentacion'])
                    precio = f"${p['Precio']:,}".replace(",", ".")
                    texto += f"• {presentacion_limpia}  ->  {precio}\n"
                texto += "\n¿Te gustaría que agendemos alguna de estas presentaciones?"

            st.write("### Copia este bloque para WhatsApp:")
            st.code(texto, language="text")
    else:
        st.warning("Producto no encontrado.")
