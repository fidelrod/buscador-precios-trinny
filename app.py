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

# 1. Configuración de conexión desde los "Secrets"
@st.cache_resource
def conectar_db():
    key_dict = json.loads(st.secrets["textkey"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    return firestore.Client(credentials=creds)

db = conectar_db()

# 2. Descargar datos de Firestore (Caché por 5 min)
@st.cache_data(ttl=300)
def obtener_inventario():
    inventario = []
    docs = db.collection("Inventario_Precios").stream()
    for doc in docs:
        inventario.append(doc.to_dict())
    return inventario

datos = obtener_inventario()

# 3. Interfaz de búsqueda
busqueda = st.text_input("Escribe la marca o producto (ej. Similac):").strip().upper()

if busqueda:
    # Filtrar datos
    filtrados = [prod for prod in datos if busqueda in prod.get("Familia_Producto", "").upper()]

    if filtrados:
        # Obtenemos familias únicas y las ordenamos
        familias = sorted(list(set(p["Familia_Producto"] for p in filtrados)))
        
        # Opción para enviar todo si hay más de una referencia
        if len(familias) > 1:
            familias.insert(0, "ENVIAR TODAS LAS REFERENCIAS")
            
        seleccion = st.selectbox("Selecciona la referencia:", familias)

        if seleccion:
            # Lógica de construcción del mensaje con negritas
            texto = ""
            
            if seleccion == "ENVIAR TODAS LAS REFERENCIAS":
                # Título principal en negrita
                texto = f"*Portafolio: {busqueda.capitalize()}*\n\n"
                for fam in familias[1:]:
                    # Título de la familia en negrita
                    texto += f"*{fam.title()}*\n"
                    for p in [p for p in filtrados if p["Familia_Producto"] == fam]:
                        presentacion_limpia = limpiar_presentacion(p['Presentacion'])
                        precio = f"${p['Precio']:,}".replace(",", ".")
                        texto += f"• {presentacion_limpia}  ->  {precio}\n"
                    texto += "\n"
                texto += "¿Cuál de estas opciones preparamos para tu despacho?"
            
            else:
                # Caso individual: Encabezado/Producto principal en negrita
                encabezado = seleccion.title()
                texto = f"*{encabezado}*\n\n"
                
                bloque = [p for p in filtrados if p["Familia_Producto"] == seleccion]
                for p in bloque:
                    presentacion_limpia = limpiar_presentacion(p['Presentacion'])
                    precio = f"${p['Precio']:,}".replace(",", ".")
                    texto += f"• {presentacion_limpia}  ->  {precio}\n"
                
                texto += "\n¿Te gustaría que agendemos alguna de estas presentaciones?"

            st.write("### Copia este bloque para WhatsApp:")
            st.code(texto, language="text")
    else:
        st.warning("Producto no encontrado.")
