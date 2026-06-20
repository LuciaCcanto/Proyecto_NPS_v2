import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.title("📊 Sistema NPS Pro")

# Lógica para categorizar NPS
def clasificar_nps(puntos):
    if puntos >= 9: return "Promotor"
    elif puntos >= 7: return "Pasivo"
    else: return "Detractor"

puntuacion = st.slider("¿Qué tan probable es que nos recomiendes?", 0, 10, 5)
comentario = st.text_area("¿Algún comentario adicional?")

if st.button("Enviar Calificación"):
    categoria = clasificar_nps(puntuacion)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    nuevo_dato = pd.DataFrame([{
        "Fecha": fecha, 
        "Puntuacion": puntuacion, 
        "Categoria": categoria, 
        "Comentario": comentario
    }])
    
    archivo = "respuestas_nps.csv"
    # Si no existe el archivo, creamos con encabezados. Si existe, añadimos sin encabezados.
    file_exists = os.path.exists(archivo)
    nuevo_dato.to_csv(archivo, mode='a', index=False, header=not file_exists)
    
    st.success("¡Respuesta guardada como " + categoria + "!")

# --- PARTE DE ADMINISTRACIÓN ---
st.divider()
st.subheader("Panel de Resultados")
if st.button("Ver datos recolectados"):
    if os.path.exists("respuestas_nps.csv"):
        df = pd.read_csv("respuestas_nps.csv")
        st.dataframe(df) # Esto muestra la tabla bonita en la web
    else:
        st.write("Aún no hay datos.")
        