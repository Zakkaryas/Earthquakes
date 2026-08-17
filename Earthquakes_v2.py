import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

def obtener_ultima_fecha_consulta(nombre_archivo):
    """Obtiene la última fecha de consulta del archivo JSON"""
    if not os.path.exists(nombre_archivo):
        return None
    
    try:
        with open(nombre_archivo, "r", encoding="utf-8") as f:
            historial = json.load(f)
        
        if historial and len(historial) > 0:
            # Obtener la última fecha de consulta
            ultima_consulta = historial[-1].get("fecha_consulta")
            if ultima_consulta:
                return datetime.strptime(ultima_consulta, '%Y-%m-%d %H:%M:%S')
    except (json.JSONDecodeError, KeyError, ValueError):
        pass
    
    return None

def monitorear_y_guardar_sismos():
    nombre_archivo = Path(__file__).parent / "historial_sismos.json"

    # Obtener la última fecha de consulta del JSON
    ultima_fecha = obtener_ultima_fecha_consulta(nombre_archivo)
    
    if ultima_fecha:
        # Calcular días desde la última consulta
        dias_desde_ultima = (datetime.now() - ultima_fecha).days
        print(f"Última consulta registrada: {ultima_fecha.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Días transcurridos: {dias_desde_ultima}")
        
        # Determinar el parámetro de la API según el tiempo transcurrido
        if dias_desde_ultima <= 1:
            url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
            print("Consultando sismos de las últimas 24 horas...")
        elif dias_desde_ultima <= 7:
            url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson"
            print(f"Consultando sismos de la última semana (desde {ultima_fecha.strftime('%Y-%m-%d')})...")
        elif dias_desde_ultima <= 30:
            url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_month.geojson"
            print(f"Consultando sismos del último mes (desde {ultima_fecha.strftime('%Y-%m-%d')})...")
        else:
            # Para períodos más largos, usar la API de búsqueda personalizada
            url = None
            print("El período es muy extenso. Usando API de búsqueda personalizada...")
    else:
        # Si no hay historial, obtener solo los datos de hoy
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
        print("No hay historial previo. Consultando sismos de hoy...")
    
    print("Conectando con el Servicio Geológico de EE.UU. (USGS)...")
    
    try:
        # Si se necesita un período mayor a 30 días, usar la API de búsqueda
        if url is None and ultima_fecha:
            # Formatear fechas para la API de búsqueda del USGS
            start_date = ultima_fecha.strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # URL de la API de búsqueda del USGS
            url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime={start_date}&endtime={end_date}&minmagnitude=2.5"
            print(f"Buscando sismos desde {start_date} hasta {end_date}...")
        
        respuesta = requests.get(url, timeout=30)
        respuesta.raise_for_status()
        
        datos = respuesta.json()
        sismos = datos.get("features", [])
        
        # Filtrar sismos desde la última fecha de consulta hasta hoy
        sismos_actuales = []
        sismos_nuevos = 0
        
        for sismo in sismos:
            propiedades = sismo.get("properties", {})
            geometria = sismo.get("geometry", {})
            
            # Convertir timestamp Unix (milisegundos) a formato legible
            timestamp = propiedades.get("time") / 1000
            fecha_sismo = datetime.fromtimestamp(timestamp)
            fecha_sismo_str = fecha_sismo.strftime('%Y-%m-%d %H:%M:%S')
            coordenadas = geometria.get("coordinates", [0, 0, 0])
            
            # Filtrar solo sismos desde la última fecha de consulta
            if ultima_fecha and fecha_sismo <= ultima_fecha:
                continue  # Saltar sismos anteriores a la última consulta
            
            sismos_actuales.append({
                "id": sismo.get("id"),
                "magnitud": propiedades.get("mag"),
                "lugar": propiedades.get("place"),
                "fecha_evento": fecha_sismo_str,
                "latitud": coordenadas[1],
                "longitud": coordenadas[0],
                "profundidad_km": coordenadas[2]
            })
            sismos_nuevos += 1
        
        # Capturar la fecha y hora exacta de la consulta actual
        fecha_consulta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Cargar el historial existente
        if os.path.exists(nombre_archivo):
            with open(nombre_archivo, "r", encoding="utf-8") as f:
                try:
                    historial = json.load(f)
                except json.JSONDecodeError:
                    historial = []
        else:
            historial = []
        
        # Estructurar el bloque de esta consulta
        nuevo_registro = {
            "fecha_consulta": fecha_consulta,
            "periodo_desde": ultima_fecha.strftime('%Y-%m-%d %H:%M:%S') if ultima_fecha else "inicio",
            "periodo_hasta": fecha_consulta,
            "total_sismos_nuevos": sismos_nuevos,
            "sismos": sismos_actuales
        }
        
        # Añadirlo al registro histórico general
        historial.append(nuevo_registro)
        
        # Guardar todo el bloque actualizado
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            json.dump(historial, f, ensure_ascii=False, indent=4)
        
        print(f"\n✅ ¡Éxito! Se encontraron {sismos_nuevos} sismos nuevos desde la última consulta")
        print(f"Registro guardado bajo la marca de tiempo: {fecha_consulta}")
        
        if sismos_nuevos == 0:
            print("No se detectaron sismos nuevos en este período.")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error de conexión: {e}")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")

if __name__ == "__main__":
    monitorear_y_guardar_sismos()