"""
Mapa de Colombia - Filtros selectivos
- Filtros: Caudal (0.15-0.50), Pendiente (>0.05)
- VSS (Viviendas Sin Servicio): 🏠 - empieza en 0
- Distancia al municipio: 🏘️ - empieza en máximo
- FILTRO ESPACIAL: Solo Parques Arqueológicos y Parques Nacionales (PNN)
- Las demás capas solo se muestran visualmente (NO excluyen puntos)
- CALCULA: Distancia a la capital MÁS CERCANA (puede ser de otro departamento)
"""

import geopandas as gpd
import folium
from folium import plugins
import requests
import pandas as pd
import json
import math
import warnings
import urllib3
import zipfile

# Suprimir warnings
warnings.filterwarnings('ignore')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ====================================================================
# CONFIGURACIÓN
# ====================================================================

RUTA_SHAPEFILE_PUNTOS = r"vss_2024.zip"

# Control de capas
DESCARGAR_CAPAS = True  # Cambiar a False si el servidor sig.cicolombiaenaccion.org tiene problemas

# Valores iniciales
CAUDAL_MIN_INICIAL = 0.15
CAUDAL_MAX_INICIAL = 0.50
PENDIENTE_MIN_INICIAL = 0.05

TAMAÑO_PUNTOS = 2

# Nombres de columnas
COLUMNA_CAUDAL = "Caudal_med"
COLUMNA_PENDIENTE = "Pendiente"
COLUMNA_MUNICIPIO = "Municipio"
COLUMNA_VSS = "VSS"
COLUMNA_DISTANCIA = "Distancia1"

# Capitales departamentales con coordenadas
CAPITALES_DEPARTAMENTOS = {
    'AMAZONAS': {'capital': 'Leticia', 'lat': -4.2153, 'lon': -69.9406},
    'ANTIOQUIA': {'capital': 'Medellín', 'lat': 6.2442, 'lon': -75.5812},
    'ARAUCA': {'capital': 'Arauca', 'lat': 7.0836, 'lon': -70.7591},
    'ATLANTICO': {'capital': 'Barranquilla', 'lat': 10.9639, 'lon': -74.7964},
    'BOLIVAR': {'capital': 'Cartagena', 'lat': 10.3910, 'lon': -75.4794},
    'BOYACA': {'capital': 'Tunja', 'lat': 5.5353, 'lon': -73.3678},
    'CALDAS': {'capital': 'Manizales', 'lat': 5.0689, 'lon': -75.5174},
    'CAQUETA': {'capital': 'Florencia', 'lat': 1.6144, 'lon': -75.6062},
    'CASANARE': {'capital': 'Yopal', 'lat': 5.3378, 'lon': -72.3959},
    'CAUCA': {'capital': 'Popayán', 'lat': 2.4419, 'lon': -76.6063},
    'CESAR': {'capital': 'Valledupar', 'lat': 10.4631, 'lon': -73.2532},
    'CHOCO': {'capital': 'Quibdó', 'lat': 5.6947, 'lon': -76.6611},
    'CORDOBA': {'capital': 'Montería', 'lat': 8.7479, 'lon': -75.8814},
    'CUNDINAMARCA': {'capital': 'Bogotá', 'lat': 4.7110, 'lon': -74.0721},
    'GUAINIA': {'capital': 'Inírida', 'lat': 3.8653, 'lon': -67.9239},
    'GUAVIARE': {'capital': 'San José del Guaviare', 'lat': 2.5697, 'lon': -72.6458},
    'HUILA': {'capital': 'Neiva', 'lat': 2.9273, 'lon': -75.2819},
    'LA GUAJIRA': {'capital': 'Riohacha', 'lat': 11.5444, 'lon': -72.9072},
    'MAGDALENA': {'capital': 'Santa Marta', 'lat': 11.2408, 'lon': -74.1990},
    'META': {'capital': 'Villavicencio', 'lat': 4.1420, 'lon': -73.6266},
    'NARIÑO': {'capital': 'Pasto', 'lat': 1.2136, 'lon': -77.2811},
    'NORTE DE SANTANDER': {'capital': 'Cúcuta', 'lat': 7.8939, 'lon': -72.5078},
    'PUTUMAYO': {'capital': 'Mocoa', 'lat': 1.1514, 'lon': -76.6428},
    'QUINDIO': {'capital': 'Armenia', 'lat': 4.5339, 'lon': -75.6811},
    'RISARALDA': {'capital': 'Pereira', 'lat': 4.8133, 'lon': -75.6961},
    'ARCHIPIELAGO SAN ANDRES Y PROVIDENCIA': {'capital': 'San Andrés', 'lat': 12.5847, 'lon': -81.7006},
    'SANTANDER': {'capital': 'Bucaramanga', 'lat': 7.1195, 'lon': -73.1227},
    'SUCRE': {'capital': 'Sincelejo', 'lat': 9.3047, 'lon': -75.3978},
    'TOLIMA': {'capital': 'Ibagué', 'lat': 4.4389, 'lon': -75.2322},
    'VALLE DEL CAUCA': {'capital': 'Cali', 'lat': 3.4516, 'lon': -76.5320},
    'VAUPES': {'capital': 'Mitú', 'lat': 1.2533, 'lon': -70.1733},
    'VICHADA': {'capital': 'Puerto Carreño', 'lat': 6.1850, 'lon': -67.4860}
}

BASE_URL = "https://sig.cicolombiaenaccion.org/server/rest/services/Hosted/biodiversidad_ci_vista/FeatureServer"

CAPAS_CONFIG = {
    'tierras_negras': {'id': 1, 'nombre': 'Tierras Comunidades Negras', 'color': '#8B4513', 'fill_opacity': 0.3},
    'resguardo_indigena': {'id': 2, 'nombre': 'Resguardos Indígenas', 'color': '#FF8C00', 'fill_opacity': 0.3},
    'parque_arqueologico': {'id': 3, 'nombre': 'Parques Arqueológicos', 'color': '#DAA520', 'fill_opacity': 0.4},
    'complejos_paramo': {'id': 4, 'nombre': 'Complejos de Páramo', 'color': '#87CEEB', 'fill_opacity': 0.4},
    'area_proteccion_local': {'id': 5, 'nombre': 'Áreas Protección Local', 'color': '#90EE90', 'fill_opacity': 0.3},
    'area_proteccion_regional': {'id': 6, 'nombre': 'Áreas Protección Regional', 'color': '#3CB371', 'fill_opacity': 0.3},
    'limite_rnsc': {'id': 7, 'nombre': 'Reservas Naturales (RNSC)', 'color': '#228B22', 'fill_opacity': 0.3},
    'limite_runap': {'id': 8, 'nombre': 'Áreas Protegidas (RUNAP)', 'color': '#006400', 'fill_opacity': 0.3},
    'limite_pnn': {'id': 9, 'nombre': 'Parques Nacionales (PNN)', 'color': '#004d00', 'fill_opacity': 0.4},
    'reservas_forestales': {'id': 10, 'nombre': 'Reservas Forestales', 'color': '#2F4F4F', 'fill_opacity': 0.3},
}

# Nombres de columnas
COLUMNA_CAUDAL = "Caudal_med"
COLUMNA_PENDIENTE = "Pendiente"
COLUMNA_MUNICIPIO = "Municipio"
COLUMNA_VSS = "VSS"
COLUMNA_DISTANCIA = "Distancia1"
COLUMNA_CAIDA = "Caida_hidr"
COLUMNA_POTENCIA_K = "Potencia_k"
COLUMNA_REGION = "Region"
COLUMNA_ZONA_CLIMA = "Zona_clima"

# ====================================================================

# Eficiencias de cada tipo de turbina
EFICIENCIAS_TURBINAS = {
    'Francis': 0.92,
    'PAT': 0.86,
    'Pelton': 0.90,
    'Kaplan': 0.89,
    'Low Head': 0.89,
    'Turgo': 0.87,
    'Cross Flow': 0.70,
    'Deriaz': 0.90,
    'Bulbo': 0.90
}

# Costos CAPEX (USD/kW) de cada tipo de turbina
COSTOS_CAPEX = {
    'Francis': 595,
    'PAT': 100,
    'Pelton': 300,
    'Kaplan': 425,
    'Low Head': 425,
    'Turgo': 295,
    'Cross Flow': 200,
    'Deriaz': 350,
    'Bulbo': 310
}

# Parámetros para costes detallados

# Tabla 1: % Instalación según complejidad
COMPLEJIDAD_INSTALACION = {
    'PAT': 0.10,
    'Cross Flow': 0.15,
    'Francis': 0.20,
    'Pelton': 0.20,
    'Kaplan': 0.20,
    'Turgo': 0.20,
    'Deriaz': 0.20,
    'Bulbo': 0.20,
    'Low Head': 0.20
}

# Tabla 2: Multiplicador impacto ambiental
MULTIPLICADOR_IMPACTO = {
    'PAT': 0.8,
    'Cross Flow': 0.8,
    'Bulbo': 0.8,
    'Turgo': 1.0,
    'Francis': 1.3,
    'Pelton': 1.3,
    'Kaplan': 1.3,
    'Deriaz': 1.3,
    'Low Head': 1.3
}

# Tabla 3: Multiplicador transporte por turbina
MULTIPLICADOR_TRANSPORTE = {
    'PAT': 2.0,
    'Pelton': 2.0,
    'Cross Flow': 3.5,
    'Bulbo': 3.5,
    'Francis': 5.0,
    'Kaplan': 5.0,
    'Turgo': 5.0,
    'Deriaz': 5.0,
    'Low Head': 5.0
}

# Tabla 4: Multiplicador por región
MULTIPLICADOR_REGION = {
    'Región Pacífico': 1.6,
    'Región Eje Cafetero – Antioquia': 1.4,
    'Región Centro Sur': 1.3,
    'Región Centro Oriente': 1.2,
    'Región Caribe': 1.0,
    'Región Llano': 1.0,
    '': 1.2  # Sin dato
}

# Tabla 5: Dificultad de turbina
DIFICULTAD_TURBINA = {
    'PAT': 1,
    'Pelton': 1,
    'Cross Flow': 2,
    'Bulbo': 2,
    'Francis': 3,
    'Kaplan': 3,
    'Turgo': 3,
    'Deriaz': 3,
    'Low Head': 3
}

def calcular_costes_detallados(tipo_turbina, potencia_kw, caida_m, dist_capital_m, region):
    """
    Calcula CAPEX detallado por partidas y OPEX para una turbina
    
    Args:
        tipo_turbina: Tipo de turbina
        potencia_kw: Potencia en kW
        caida_m: Caída hidráulica en metros
        dist_capital_m: Distancia a capital en metros
        region: Región del punto
    
    Returns:
        Diccionario con todos los costes detallados
    """
    costes = {}
    
    # 1. Coste turbina (ya calculado previamente)
    coste_turbina = potencia_kw * COSTOS_CAPEX[tipo_turbina]
    costes['coste_turbina'] = coste_turbina
    
    # 2. Coste equipos sin turbina
    coste_equipos = coste_turbina * 0.8
    costes['coste_equipos'] = coste_equipos
    
    # 3. Coste obra civil
    Cbase = 2200
    coste_obra_civil = Cbase * potencia_kw
    costes['coste_obra_civil'] = coste_obra_civil
    
    # 4. Costes instalación y puesta en marcha
    complejidad = COMPLEJIDAD_INSTALACION[tipo_turbina]
    coste_instalacion = (coste_equipos + coste_turbina) * complejidad
    costes['coste_instalacion'] = coste_instalacion
    
    # 5. Coste línea de conexión eléctrica
    if potencia_kw < 50:
        Cbase_linea = 15000
        F = 400
    else:
        Cbase_linea = 20000
        F = 500
    coste_linea = Cbase_linea + (potencia_kw * F)
    costes['coste_linea'] = coste_linea
    
    # 6. Costes ambientales
    M_impacto = MULTIPLICADOR_IMPACTO[tipo_turbina]
    coste_ambiental = (8000 + 100 * potencia_kw) * M_impacto
    costes['coste_ambiental'] = coste_ambiental
    
    # 7. Coste transporte
    dist_capital_km = dist_capital_m / 1000
    D_real = dist_capital_km * 1.8  # Factor topografía
    
    # Peso estimado
    if potencia_kw < 50:
        W = potencia_kw * 0.150  # 150 kg/kW en toneladas
    else:
        W = potencia_kw * 0.120  # 120 kg/kW en toneladas
    
    M_turb = MULTIPLICADOR_TRANSPORTE[tipo_turbina]
    M_region = MULTIPLICADOR_REGION.get(region, 1.2)
    
    coste_transporte_base = 8.0 * D_real * W * M_turb * M_region
    
    # Costes adicionales de transporte
    dificultad_turb = DIFICULTAD_TURBINA[tipo_turbina]
    C_movilizacion = 3000 * dificultad_turb * M_region
    C_logistica = 100 * potencia_kw * M_region
    
    coste_transporte = coste_transporte_base + C_movilizacion + C_logistica
    costes['coste_transporte'] = coste_transporte
    
    # 8. Otros costes
    suma_parcial = (coste_turbina + coste_equipos + coste_obra_civil + 
                    coste_instalacion + coste_linea + coste_ambiental + coste_transporte)
    otros_costes = suma_parcial * 0.05
    costes['otros_costes'] = otros_costes
    
    # CAPEX Total
    capex_total = suma_parcial + otros_costes
    costes['capex_total'] = capex_total
    
    # OPEX
    opex = capex_total * 0.03
    costes['opex'] = opex
    
    return costes

def determinar_tipo_turbina(caudal_m3s, caida_m, potencia_k):
    """
    Determina el tipo de turbina aplicable según caudal y caída hidráulica
    usando polígonos basados en el diagrama de selección de turbinas
    y calcula la potencia y CAPEX para cada tipo
    
    Args:
        caudal_m3s: Caudal en m³/s
        caida_m: Caída hidráulica en metros
        potencia_k: Potencia_k del punto (kW)
    
    Returns:
        Lista de tipos de turbina aplicables con sus potencias y CAPEX
    """
    from shapely.geometry import Point, Polygon
    
    # Conversión de unidades
    caudal_cfs = caudal_m3s * 35.3147  # m³/s a pies³/s
    caida_ft = caida_m * 3.28084  # metros a pies
    
    # Crear punto con las coordenadas del sitio
    punto = Point(caudal_cfs, caida_ft)
    
    turbinas_aplicables = []
    
    # Definir polígonos de cada tipo de turbina basados en el diagrama
    # Coordenadas: (discharge_cfs, head_ft)
    
    # Low Head (naranja) - parte inferior
    low_head = Polygon([
        (1, 1), (10000, 1), (10000, 20), (1, 20)
    ])
    
    # PAT (azul claro) - izquierda inferior-media
    pat = Polygon([
        (1, 30), (30, 30), (30, 300), (1, 300)
    ])
    
    # Kaplan (azul oscuro) - derecha inferior-media
    kaplan = Polygon([
        (100, 10), (10000, 10), (10000, 150), (100, 150)
    ])
    
    # Cross Flow (rojo) - centro-izquierda
    cross_flow = Polygon([
        (1, 10), (200, 10), (200, 400), (1, 400)
    ])
    
    # Turgo (verde) - izquierda media-alta
    turgo = Polygon([
        (1, 100), (500, 100), (500, 1000), (1, 1000)
    ])
    
    # Francis (cian) - centro amplio
    francis = Polygon([
        (10, 50), (3000, 50), (3000, 300), (200, 300),
        (200, 3000), (10, 3000)
    ])
    
    # Pelton (morado oscuro) - superior izquierdo
    pelton = Polygon([
        (1, 300), (200, 300), (200, 5000), (1, 5000)
    ])
    
    # Verificar en qué polígonos cae el punto y calcular potencia y CAPEX
    # Nueva fórmula: Potencia (kW) = Potencia_k × 0.9 × η
    # CAPEX (USD) = Potencia (kW) × Costo_unitario (USD/kW)
    
    if pelton.contains(punto):
        potencia = potencia_k * 0.9 * EFICIENCIAS_TURBINAS['Pelton']
        capex = potencia * COSTOS_CAPEX['Pelton']
        turbinas_aplicables.append({'tipo': 'Pelton', 'potencia': potencia, 'capex': capex})
    
    if turgo.contains(punto):
        potencia = potencia_k * 0.9 * EFICIENCIAS_TURBINAS['Turgo']
        capex = potencia * COSTOS_CAPEX['Turgo']
        turbinas_aplicables.append({'tipo': 'Turgo', 'potencia': potencia, 'capex': capex})
    
    if francis.contains(punto):
        potencia = potencia_k * 0.9 * EFICIENCIAS_TURBINAS['Francis']
        capex = potencia * COSTOS_CAPEX['Francis']
        turbinas_aplicables.append({'tipo': 'Francis', 'potencia': potencia, 'capex': capex})
    
    if cross_flow.contains(punto):
        potencia = potencia_k * 0.9 * EFICIENCIAS_TURBINAS['Cross Flow']
        capex = potencia * COSTOS_CAPEX['Cross Flow']
        turbinas_aplicables.append({'tipo': 'Cross Flow', 'potencia': potencia, 'capex': capex})
    
    if kaplan.contains(punto):
        potencia = potencia_k * 0.9 * EFICIENCIAS_TURBINAS['Kaplan']
        capex = potencia * COSTOS_CAPEX['Kaplan']
        turbinas_aplicables.append({'tipo': 'Kaplan', 'potencia': potencia, 'capex': capex})
    
    if pat.contains(punto):
        potencia = potencia_k * 0.9 * EFICIENCIAS_TURBINAS['PAT']
        capex = potencia * COSTOS_CAPEX['PAT']
        turbinas_aplicables.append({'tipo': 'PAT', 'potencia': potencia, 'capex': capex})
    
    if low_head.contains(punto):
        potencia = potencia_k * 0.9 * EFICIENCIAS_TURBINAS['Low Head']
        capex = potencia * COSTOS_CAPEX['Low Head']
        turbinas_aplicables.append({'tipo': 'Low Head', 'potencia': potencia, 'capex': capex})
    
    return turbinas_aplicables, caudal_cfs, caida_ft

def calcular_distancia_haversine(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia entre dos puntos en metros usando la fórmula de Haversine
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371000  # Radio de la Tierra en metros
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distancia = R * c
    return distancia

def descargar_capa_desde_api(layer_id, nombre_capa):
    url = f"{BASE_URL}/{layer_id}/query"
    params = {'where': '1=1', 'outFields': '*', 'f': 'geojson', 'returnGeometry': 'true'}
    
    try:
        print(f"  Descargando: {nombre_capa}...", end=" ")
        
        # Crear sesión con configuración personalizada
        session = requests.Session()
        session.verify = False
        
        # Headers personalizados
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }
        
        # Realizar petición con reintentos
        max_retries = 3
        for intento in range(max_retries):
            try:
                response = session.get(url, params=params, headers=headers, timeout=60)
                response.raise_for_status()
                geojson_data = response.json()
                break
            except Exception as e:
                if intento < max_retries - 1:
                    print(f"⏳ Reintento {intento + 1}...", end=" ")
                    continue
                else:
                    raise e
        
        if 'features' in geojson_data and len(geojson_data['features']) > 0:
            gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
            if gdf.crs is None:
                gdf.set_crs("EPSG:4326", inplace=True)
            elif gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")
            print(f"✓ {len(gdf)}")
            return gdf
        print(f"⚠ Sin datos")
        return None
    except Exception as e:
        print(f"✗ Error: {str(e)[:100]}")
        return None

def cargar_shapefile_puntos(ruta):
    print("\n" + "="*70)
    print("CARGANDO SHAPEFILE")
    print("="*70)
    
    try:
        if ruta.lower().endswith(".zip"):
            # Crear carpeta temporal
            extract_dir = "temp_shp"
            if not os.path.exists(extract_dir):
                os.makedirs(extract_dir)
            
            # Extraer todos los archivos del zip
            with zipfile.ZipFile(ruta, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Buscar el .shp dentro de la carpeta temporal
            shp_files = [f for f in os.listdir(extract_dir) if f.endswith(".shp")]
            if len(shp_files) == 0:
                raise FileNotFoundError("No se encontró ningún archivo .shp dentro del ZIP")
            
            ruta_shp = os.path.join(extract_dir, shp_files[0])
            puntos = gpd.read_file(ruta_shp)
        
        else:
            # Leer shapefile directamente
            puntos = gpd.read_file(ruta)
        
        # Asegurar CRS EPSG:4326
        if puntos.crs != "EPSG:4326":
            puntos = puntos.to_crs("EPSG:4326")
        
        print(f"✓ {len(puntos)} puntos cargados")
        return puntos
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def filtrar_puntos_fuera_de_areas(puntos, capas_areas):
    print("\n" + "="*70)
    print("FILTRO ESPACIAL - SOLO PARQUES ARQUEOLÓGICOS Y PNN")
    print("="*70 + "\n")
    
    puntos_filtrados = puntos.copy()
    total = len(puntos_filtrados)
    
    # SOLO estas capas son restrictivas (excluyen puntos)
    CAPAS_RESTRICTIVAS = ['parque_arqueologico', 'limite_pnn']
    
    print("⚠️  CAPAS RESTRICTIVAS (excluyen puntos):")
    print("   • Parques Arqueológicos")
    print("   • Parques Nacionales (PNN)")
    print("\n📍 Las demás capas solo se muestran en el mapa (NO excluyen puntos)\n")
    
    # Verificar si hay capas restrictivas disponibles
    capas_disponibles = [key for key in CAPAS_RESTRICTIVAS if key in capas_areas and capas_areas[key] is not None]
    
    if len(capas_disponibles) == 0:
        print("⚠️  ADVERTENCIA: No se cargaron capas restrictivas. Todos los puntos serán incluidos.\n")
    
    for key, datos in capas_areas.items():
        if datos is None:
            continue
        
        # Solo filtrar si está en la lista de restrictivas
        if key not in CAPAS_RESTRICTIVAS:
            continue
        
        gdf_area = datos['geodataframe']
        config = datos['config']
        print(f"  Filtrando contra {config['nombre']}...", end=" ")
        
        try:
            puntos_dentro = gpd.sjoin(puntos_filtrados, gdf_area, how='inner', predicate='within')
            indices = puntos_dentro.index.unique()
            puntos_filtrados = puntos_filtrados.drop(indices)
            eliminados = len(indices)
            print(f"✓ -{eliminados:,}, quedan {len(puntos_filtrados):,}")
        except Exception as e:
            print(f"⚠ Error: {e}")
    
    print(f"\n{'='*70}")
    print(f"✓ FILTRO ESPACIAL COMPLETADO")
    print(f"  Inicial: {total:,} | Fuera áreas restrictivas: {len(puntos_filtrados):,} ({len(puntos_filtrados)/total*100:.1f}%)")
    print(f"  Capas filtradas aplicadas: {len(capas_disponibles)}/{len(CAPAS_RESTRICTIVAS)}")
    print(f"{'='*70}\n")
    
    return puntos_filtrados

def crear_mapa_interactivo(puntos_filtrados, capas_areas, total_original):
    print("Creando mapa interactivo...\n")
    
    centro_lat = puntos_filtrados.geometry.y.mean()
    centro_lon = puntos_filtrados.geometry.x.mean()
    
    mapa = folium.Map(location=[centro_lat, centro_lon], zoom_start=6, tiles='cartodbdark_matter')
    
    folium.TileLayer('OpenStreetMap', name='Mapa Claro').add_to(mapa)
    folium.TileLayer('cartodbdark_matter', name='Mapa Oscuro ⚫').add_to(mapa)
    folium.TileLayer('cartodbpositron', name='Mapa Minimalista').add_to(mapa)
    
    for key, datos in capas_areas.items():
        if datos is None:
            continue
        gdf = datos['geodataframe']
        config = datos['config']
        grupo = folium.FeatureGroup(name=config['nombre'], show=True)
        style_function = lambda x, color=config['color'], opacity=config['fill_opacity']: {
            'fillColor': color, 'fillOpacity': opacity, 'color': color, 'weight': 2, 'opacity': 0.8
        }
        folium.GeoJson(gdf, style_function=style_function).add_to(grupo)
        grupo.add_to(mapa)
    
    puntos_data = []
    columnas = [col for col in puntos_filtrados.columns if col != 'geometry']
    
    print(f"Preparando {len(puntos_filtrados):,} puntos...")
    
    # Calcular máximos reales y redondear
    if COLUMNA_VSS in puntos_filtrados.columns:
        vss_valores = puntos_filtrados[COLUMNA_VSS].dropna()
        vss_max_real = math.ceil(vss_valores.max()) if len(vss_valores) > 0 else 10
        vss_min_inicial = 0
        print(f"  VSS: mín=0, máx={vss_max_real} (redondeado)")
    else:
        vss_max_real = 10
        vss_min_inicial = 0
    
    if COLUMNA_DISTANCIA in puntos_filtrados.columns:
        dist_valores = puntos_filtrados[COLUMNA_DISTANCIA].dropna()
        dist_max_real = math.ceil(dist_valores.max()) if len(dist_valores) > 0 else 100
        print(f"  Distancia: máx={dist_max_real} (redondeado)")
    else:
        dist_max_real = 100
    
    for idx, row in puntos_filtrados.iterrows():
        # Obtener departamento del punto
        departamento = str(row['Departamen']) if 'Departamen' in row and pd.notna(row['Departamen']) else ''
        
        # Encontrar la capital MÁS CERCANA al punto (puede ser de otro departamento)
        punto_lat = row.geometry.y
        punto_lon = row.geometry.x
        
        capital_mas_cercana = None
        distancia_minima = float('inf')
        depto_capital_cercana = ''
        
        for depto, capital_info in CAPITALES_DEPARTAMENTOS.items():
            dist = calcular_distancia_haversine(
                punto_lat, punto_lon,
                capital_info['lat'], capital_info['lon']
            )
            if dist < distancia_minima:
                distancia_minima = dist
                capital_mas_cercana = capital_info['capital']
                depto_capital_cercana = depto
        
        # Calcular distancias
        if capital_mas_cercana:
            dist_punto_capital = distancia_minima
            # Distancia del núcleo poblado a la capital (aproximada)
            distancia1 = float(row[COLUMNA_DISTANCIA]) if COLUMNA_DISTANCIA in row and pd.notna(row[COLUMNA_DISTANCIA]) else 0
            dist_nucleo_capital = max(0, dist_punto_capital - distancia1)
        else:
            capital_mas_cercana = 'N/A'
            depto_capital_cercana = ''
            dist_punto_capital = 0
            dist_nucleo_capital = 0
        
        # Obtener caída hidráulica, caudal, potencia_k, región, zona_clima y calcular turbinas aplicables
        caida = float(row[COLUMNA_CAIDA]) if COLUMNA_CAIDA in row and pd.notna(row[COLUMNA_CAIDA]) else 0
        caudal = float(row[COLUMNA_CAUDAL]) if pd.notna(row[COLUMNA_CAUDAL]) else 0
        potencia_k = float(row[COLUMNA_POTENCIA_K]) if COLUMNA_POTENCIA_K in row and pd.notna(row[COLUMNA_POTENCIA_K]) else 0
        region = str(row[COLUMNA_REGION]) if COLUMNA_REGION in row and pd.notna(row[COLUMNA_REGION]) else ''
        zona_clima = str(row[COLUMNA_ZONA_CLIMA]) if COLUMNA_ZONA_CLIMA in row and pd.notna(row[COLUMNA_ZONA_CLIMA]) else ''
        vss = float(row[COLUMNA_VSS]) if COLUMNA_VSS in row and pd.notna(row[COLUMNA_VSS]) else 0
        
        # Determinar potencia pico según zona climática
        if zona_clima in ['TEMPLADO', 'FRÍO', 'CÁLIDO SECO']:
            potencia_pico = 1.54
        elif zona_clima == 'CÁLIDO HÚMEDO':
            potencia_pico = 2.06
        else:
            potencia_pico = 1.54  # Por defecto
        
        # Calcular potencia a abastecer para cubrir las VSS
        potencia_abastecer_vss = vss * potencia_pico
        
        turbinas_data, caudal_cfs, caida_ft = determinar_tipo_turbina(caudal, caida, potencia_k)
        
        # Preparar información de turbinas con costes detallados para el mapa
        turbinas_list = []
        for t in turbinas_data:
            potencia_maxima = t['potencia']  # Esta es la potencia máxima aprovechable
            
            # Determinar si es caso híbrido y qué potencia usar para costes
            if potencia_maxima < potencia_abastecer_vss:
                # Caso híbrido: la potencia máxima no cubre las VSS requeridas
                potencia_para_costes = potencia_maxima
                vss_abastecibles = int(potencia_maxima / potencia_pico) if potencia_pico > 0 else 0  # Redondeo hacia abajo
                es_hibrida = True
            else:
                # Caso normal: la potencia máxima cubre las VSS
                potencia_para_costes = potencia_abastecer_vss
                vss_abastecibles = int(vss)  # Convertir a entero
                es_hibrida = False
            
            # Calcular costes detallados con la potencia correspondiente
            costes = calcular_costes_detallados(
                t['tipo'],
                potencia_para_costes,
                caida,
                dist_punto_capital,
                region
            )
            
            # Calcular CAPEX por VSS (usar VSS abastecibles, no VSS totales)
            capex_por_vss = costes['capex_total'] / vss_abastecibles if vss_abastecibles > 0 else 0
            
            turbinas_list.append({
                'tipo': t['tipo'],
                'potencia_maxima': round(potencia_maxima, 2),
                'potencia_abastecer_vss': round(potencia_abastecer_vss, 2),
                'potencia_usada_costes': round(potencia_para_costes, 2),
                'vss_abastecibles': vss_abastecibles,  # Ya es entero
                'es_hibrida': es_hibrida,
                'capex_simple': round(t['capex'], 2),
                'coste_turbina': round(costes['coste_turbina'], 2),
                'coste_equipos': round(costes['coste_equipos'], 2),
                'coste_obra_civil': round(costes['coste_obra_civil'], 2),
                'coste_instalacion': round(costes['coste_instalacion'], 2),
                'coste_linea': round(costes['coste_linea'], 2),
                'coste_ambiental': round(costes['coste_ambiental'], 2),
                'coste_transporte': round(costes['coste_transporte'], 2),
                'otros_costes': round(costes['otros_costes'], 2),
                'capex_total': round(costes['capex_total'], 2),
                'opex': round(costes['opex'], 2),
                'capex_por_vss': round(capex_por_vss, 2)
            })
        
        punto = {
            'lat': float(row.geometry.y),
            'lon': float(row.geometry.x),
            'id': int(idx),
            'caudal': caudal,
            'caida': caida,
            'potencia_k': potencia_k,
            'caudal_cfs': round(caudal_cfs, 2),
            'caida_ft': round(caida_ft, 2),
            'turbinas': turbinas_list,
            'pendiente': float(row[COLUMNA_PENDIENTE]) if pd.notna(row[COLUMNA_PENDIENTE]) else 0,
            'municipio': str(row[COLUMNA_MUNICIPIO]) if pd.notna(row[COLUMNA_MUNICIPIO]) else '',
            'departamento': departamento,
            'region': region,
            'zona_clima': zona_clima,
            'potencia_pico': potencia_pico,
            'vss': float(row[COLUMNA_VSS]) if COLUMNA_VSS in row and pd.notna(row[COLUMNA_VSS]) else 0,
            'distancia': float(row[COLUMNA_DISTANCIA]) if COLUMNA_DISTANCIA in row and pd.notna(row[COLUMNA_DISTANCIA]) else 0,
            'capital': capital_mas_cercana,
            'depto_capital': depto_capital_cercana,
            'dist_punto_capital': round(dist_punto_capital, 0),
            'dist_nucleo_capital': round(dist_nucleo_capital, 0),
            'todos_atributos': {}
        }
        
        for col in columnas:
            valor = row[col]
            punto['todos_atributos'][col] = str(valor) if pd.notna(valor) else 'N/A'
        
        puntos_data.append(punto)
    
    print("✓ Puntos preparados")
    
    # Panel de controles
    controles_html = f'''
    <div id="control-panel" style="position: fixed; top: 80px; left: 10px; width: 380px; 
         background: white; z-index: 9999; padding: 18px; border-radius: 10px; 
         box-shadow: 0 6px 12px rgba(0,0,0,0.4); font-family: 'Segoe UI', Arial, sans-serif; 
         max-height: 85vh; overflow-y: auto;">
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 3px solid #E54D9A; padding-bottom: 10px;">
            <h3 style="margin: 0; color: #5D0E41; font-size: 18px;">
                🎛️ Filtros Interactivos
            </h3>
            <button id="btn-minimizar" onclick="toggleMinimizar()" style="background: #E54D9A; color: white; border: none; border-radius: 50%; width: 30px; height: 30px; cursor: pointer; font-size: 16px; font-weight: bold; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2);" title="Minimizar/Maximizar">
                −
            </button>
        </div>
        
        <div id="panel-contenido">
        
        <div style="border: 2px solid #E54D9A; padding: 15px; border-radius: 8px; margin-bottom: 18px; background: #F5F3F0;">
            <h4 style="margin: 0 0 15px 0; color: #E54D9A; font-size: 15px;">Filtros</h4>
            
            <!-- Caudal -->
            <div style="margin-bottom: 20px; background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 20px; margin-right: 8px;">💧</span>
                    <label style="font-weight: 600; font-size: 13px; color: #5D0E41; flex: 1;">Caudal</label>
                </div>
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 6px;">
                    <div style="flex: 1;">
                        <div style="font-size: 11px; color: #8B8B6E; margin-bottom: 3px;">Mínimo</div>
                        <div style="font-size: 16px; font-weight: bold; color: #E54D9A;">
                            <span id="cmin">{CAUDAL_MIN_INICIAL}</span>
                        </div>
                    </div>
                    <div style="color: #C0C0B0; font-size: 18px;">-</div>
                    <div style="flex: 1; text-align: right;">
                        <div style="font-size: 11px; color: #8B8B6E; margin-bottom: 3px;">Máximo</div>
                        <div style="font-size: 16px; font-weight: bold; color: #E54D9A;">
                            <span id="cmax">{CAUDAL_MAX_INICIAL}</span>
                        </div>
                    </div>
                </div>
                <input type="range" id="caudal-min" min="0" max="1" step="0.01" value="{CAUDAL_MIN_INICIAL}" 
                       style="width: 100%; margin-bottom: 5px; height: 6px;" oninput="actualizarValores()">
                <input type="range" id="caudal-max" min="0" max="1" step="0.01" value="{CAUDAL_MAX_INICIAL}" 
                       style="width: 100%; height: 6px;" oninput="actualizarValores()">
            </div>
            
            <!-- Pendiente -->
            <div style="margin-bottom: 20px; background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 20px; margin-right: 8px;">📐</span>
                    <label style="font-weight: 600; font-size: 13px; color: #5D0E41; flex: 1;">Pendiente Mínima</label>
                    <span style="font-size: 16px; font-weight: bold; color: #E54D9A;" id="pmin">{PENDIENTE_MIN_INICIAL}</span>
                </div>
                <input type="range" id="pend-min" min="0" max="0.5" step="0.01" value="{PENDIENTE_MIN_INICIAL}" 
                       style="width: 100%; height: 6px;" oninput="actualizarValores()">
            </div>
            
            <!-- VSS MÍNIMO - ICONO 🏠 -->
            <div style="margin-bottom: 20px; background: white; padding: 12px; border-radius: 6px; border: 1px solid #e0e0e0;">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 20px; margin-right: 8px;">🏠</span>
                    <label style="font-weight: 600; font-size: 13px; color: #5D0E41; flex: 1;">VSS Mínimo</label>
                    <span style="font-size: 16px; font-weight: bold; color: #FF0066;" id="vss-min-val">{vss_min_inicial}</span>
                </div>
                <div style="font-size: 10px; color: #A8A890; margin-bottom: 4px;">
                    Viviendas Sin Servicio | Rango: 0 - {vss_max_real}
                </div>
                <input type="range" id="vss-min" min="0" max="{vss_max_real}" step="1" 
                       value="{vss_min_inicial}" style="width: 100%; height: 6px;" oninput="actualizarValores()">
            </div>
        </div>
        
        <!-- TASA DE CAMBIO -->
        <div style="margin-bottom: 18px; border: 2px solid #5D5D4D; padding: 12px; border-radius: 8px; background: #F5F3F0;">
            <label style="font-weight: 600; font-size: 13px; color: #5D0E41; display: block; margin-bottom: 8px;">
                <span style="font-size: 18px; margin-right: 6px;">💱</span>Tasa de Cambio
            </label>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <span style="font-size: 14px; font-weight: 600; color: #5D0E41;">1 USD =</span>
                <input type="number" id="tasa-cambio" value="3711.71" 
                       style="flex: 1; padding: 8px; border: 2px solid #5D5D4D; border-radius: 4px; 
                              font-size: 14px; font-weight: 600; color: #5D0E41;"
                       min="0" step="0.01">
                <span style="font-size: 14px; font-weight: 600; color: #5D0E41;">COP</span>
            </div>
            <div style="font-size: 10px; color: #5D5D4D; margin-top: 4px; font-style: italic;">
                Los costes se mostrarán en USD y COP
            </div>
        </div>
        
        <!-- FILTRO DE CAPEX MÁXIMO -->
        <div style="margin-bottom: 18px; border: 2px solid #E54D9A; padding: 12px; border-radius: 8px; background: #FFF5F8;">
            <label style="font-weight: 600; font-size: 13px; color: #5D0E41; display: block; margin-bottom: 8px;">
                <span style="font-size: 18px; margin-right: 6px;">💰</span>CAPEX Máximo (USD)
            </label>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 20px; color: #E54D9A;">$</span>
                <input type="number" id="capex-max" placeholder="Sin límite" 
                       style="flex: 1; padding: 8px; border: 2px solid #E54D9A; border-radius: 4px; 
                              font-size: 14px; font-weight: 600; color: #5D0E41;"
                       min="0" step="1000">
            </div>
            <div style="font-size: 10px; color: #5D5D4D; margin-top: 4px; font-style: italic;">
                Deja vacío para ver todos los puntos
            </div>
        </div>
        
        <!-- ESTADÍSTICAS -->
        <div style="padding: 16px; background: linear-gradient(135deg, #5D0E41 0%, #E54D9A 100%); 
             border-radius: 8px; color: white; margin-bottom: 12px; box-shadow: 0 3px 6px rgba(0,0,0,0.2); text-align: center;">
            <div style="font-size: 14px; font-weight: 600; margin-bottom: 8px;">✓ Puntos visibles</div>
            <div style="font-size: 36px; font-weight: bold;">
                <span id="count">0</span>
            </div>
        </div>
        
        <!-- FILTRO DE TURBINAS -->
        <div style="margin-bottom: 18px; border: 2px solid #8B8B6E; padding: 12px; border-radius: 8px; background: #F5F3F0;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <label style="font-weight: 600; font-size: 13px; color: #6B6B4E;">
                    <span style="font-size: 18px; margin-right: 6px;">⚡</span>Tipos de Turbina
                </label>
                <button onclick="toggleTurbinas()" style="font-size: 11px; padding: 4px 10px; cursor: pointer; 
                        background: #8B8B6E; color: white; border: none; border-radius: 4px; font-weight: 600;">
                    Todos/Ninguno
                </button>
            </div>
            <div style="max-height: 180px; overflow-y: auto; background: white; padding: 8px; border-radius: 6px; border: 1px solid #B8B8A0;">
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="turb-francis" value="Francis" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="turb-francis" style="cursor: pointer; font-size: 11px;">Francis</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="turb-pat" value="PAT" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="turb-pat" style="cursor: pointer; font-size: 11px;">PAT (Pump as Turbine)</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="turb-pelton" value="Pelton" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="turb-pelton" style="cursor: pointer; font-size: 11px;">Pelton</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="turb-kaplan" value="Kaplan" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="turb-kaplan" style="cursor: pointer; font-size: 11px;">Kaplan</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="turb-lowhead" value="Low Head" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="turb-lowhead" style="cursor: pointer; font-size: 11px;">Low Head</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="turb-turgo" value="Turgo" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="turb-turgo" style="cursor: pointer; font-size: 11px;">Turgo</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="turb-crossflow" value="Cross Flow" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="turb-crossflow" style="cursor: pointer; font-size: 11px;">Cross Flow</label>
                </div>
            </div>
        </div>
        
        <!-- FILTRO DE REGIONES -->
        <div style="margin-bottom: 18px; border: 2px solid #FF0066; padding: 12px; border-radius: 8px; background: #FFF5F8;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                <label style="font-weight: 600; font-size: 13px; color: #CC0052;">
                    <span style="font-size: 18px; margin-right: 6px;">🗺️</span>Regiones
                </label>
                <button onclick="toggleRegiones()" style="font-size: 11px; padding: 4px 10px; cursor: pointer; 
                        background: #FF0066; color: white; border: none; border-radius: 4px; font-weight: 600;">
                    Todos/Ninguno
                </button>
            </div>
            <div style="max-height: 180px; overflow-y: auto; background: white; padding: 8px; border-radius: 6px; border: 1px solid #F8A8C8;">
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="reg-pacifico" value="Región Pacífico" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="reg-pacifico" style="cursor: pointer; font-size: 11px;">Región Pacífico</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="reg-eje-cafetero" value="Región Eje Cafetero – Antioquia" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="reg-eje-cafetero" style="cursor: pointer; font-size: 11px;">Región Eje Cafetero – Antioquia</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="reg-centro-sur" value="Región Centro Sur" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="reg-centro-sur" style="cursor: pointer; font-size: 11px;">Región Centro Sur</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="reg-centro-oriente" value="Región Centro Oriente" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="reg-centro-oriente" style="cursor: pointer; font-size: 11px;">Región Centro Oriente</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="reg-caribe" value="Región Caribe" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="reg-caribe" style="cursor: pointer; font-size: 11px;">Región Caribe</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="reg-llano" value="Región Llano" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="reg-llano" style="cursor: pointer; font-size: 11px;">Región Llano</label>
                </div>
                <div style="margin: 4px 0;">
                    <input type="checkbox" id="reg-sin-dato" value="" checked style="margin-right: 6px; cursor: pointer;">
                    <label for="reg-sin-dato" style="cursor: pointer; font-size: 11px; color: #A8A890;">Sin dato</label>
                </div>
            </div>
        </div>
        
        <!-- BOTÓN MOSTRAR -->
        <button onclick="actualizar()" style="width: 100%; padding: 14px; background: #E54D9A; 
                color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; 
                font-size: 15px; box-shadow: 0 3px 6px rgba(39,174,96,0.4); transition: all 0.3s; margin-bottom: 8px;"
                onmouseover="this.style.background='#C44080'" onmouseout="this.style.background='#E54D9A'">
            ✓ Mostrar
        </button>
        
        <button onclick="resetear()" style="width: 100%; padding: 8px; background: #8B8B6E; 
                color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; 
                font-size: 11px; transition: all 0.3s; margin-bottom: 8px;"
                onmouseover="this.style.background='#8B8B6E'" onmouseout="this.style.background='#A8A890'">
            🔄 Resetear filtros
        </button>
        
        <button onclick="priorizar()" style="width: 100%; padding: 12px; background: linear-gradient(135deg, #E54D9A 0%, #FF0066 100%); 
                color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; 
                font-size: 13px; box-shadow: 0 3px 6px rgba(240,147,251,0.4); transition: all 0.3s; margin-bottom: 8px;"
                onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
            ⭐ Priorización
        </button>
        
        <!-- FILTROS DE PRIORIZACIÓN (solo visibles cuando está activa) -->
        <div id="filtros-priorizacion" style="display: none; margin-bottom: 8px; padding: 12px; background: #FFF0F5; border: 2px solid #f093fb; border-radius: 6px;">
            <div style="font-weight: bold; color: #CC0052; margin-bottom: 8px; font-size: 12px;">⚙️ Filtros de Priorización</div>
            
            <!-- Filtro Top N -->
            <div style="margin-bottom: 10px;">
                <label for="ranking-top" style="display: block; font-weight: 600; font-size: 11px; color: #555; margin-bottom: 4px;">
                    🏆 Mostrar Top:
                </label>
                <input type="number" id="ranking-top" min="1" placeholder="Ej: 10, 50, 100..." 
                       style="width: 100%; padding: 6px; border: 2px solid #f093fb; border-radius: 4px; font-size: 12px;"
                       oninput="aplicarFiltrosPriorizacion()">
                <div style="font-size: 9px; color: #CC0052; margin-top: 2px;">Deja vacío para mostrar todos</div>
            </div>
            
            <!-- Filtro Budget -->
            <div style="margin-bottom: 10px;">
                <label for="budget-max" style="display: block; font-weight: 600; font-size: 11px; color: #555; margin-bottom: 4px;">
                    💰 Budget Máximo (USD):
                </label>
                <input type="number" id="budget-max" min="0" placeholder="Ej: 500000" 
                       style="width: 100%; padding: 6px; border: 2px solid #f093fb; border-radius: 4px; font-size: 12px;"
                       oninput="aplicarFiltrosPriorizacion()">
                <div style="font-size: 9px; color: #CC0052; margin-top: 2px;">Suma CAPEX desde ranking #1</div>
            </div>
            
            <!-- Ranking por colores -->
            <div style="margin-top: 12px; padding: 10px; background: linear-gradient(90deg, #0D3B66, #1A5276, #2874A6, #5DADE2, #85C1E9, #ADD8E6); border-radius: 6px;">
                <div style="background: rgba(255,255,255,0.95); padding: 8px; border-radius: 4px;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <label for="ranking-colores" style="font-weight: 600; font-size: 11px; color: #555; cursor: pointer;">
                            🎨 Ranking por colores
                        </label>
                        <input type="checkbox" id="ranking-colores" 
                               style="width: 18px; height: 18px; cursor: pointer;"
                               onchange="aplicarFiltrosPriorizacion()">
                    </div>
                    <div style="font-size: 9px; color: #666; margin-top: 4px;">
                        🔷 Oscuro = Mejor → Claro = Peor 🔹
                    </div>
                </div>
            </div>
        </div>
        
        <button onclick="despriorizar()" id="btn-despriorizar" style="width: 100%; padding: 10px; background: #5D5D4D; 
                color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; 
                font-size: 11px; transition: all 0.3s; margin-bottom: 8px; display: none;"
                onmouseover="this.style.background='#4D4D3D'" onmouseout="this.style.background='#5D5D4D'">
            ❌ Deshacer priorización
        </button>
        
        <button onclick="mostrarAnalisisMultiescenario()" id="btn-multiescenario" style="width: 100%; padding: 10px; background: linear-gradient(135deg, #8E44AD 0%, #3498DB 100%); 
                color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; 
                font-size: 11px; transition: all 0.3s; margin-bottom: 8px; display: none;"
                onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
            📊 Análisis Multiescenario
        </button>
        
        <button onclick="descargarDatos()" style="width: 100%; padding: 12px; background: linear-gradient(135deg, #5D0E41 0%, #E54D9A 100%); 
                color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; 
                font-size: 14px; box-shadow: 0 3px 6px rgba(229,77,154,0.4); transition: all 0.3s;"
                onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
            📥 Descargar datos visibles
        </button>
        
        <button onclick="toggleParametrizacion()" style="width: 100%; padding: 12px; margin-top: 8px; background: linear-gradient(135deg, #2C3E50 0%, #3498DB 100%); 
                color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; 
                font-size: 14px; box-shadow: 0 3px 6px rgba(52,152,219,0.4); transition: all 0.3s;"
                onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
            ⚙️ Parametrización
        </button>
        
        <!-- PANEL DE PARAMETRIZACIÓN -->
        <div id="panel-parametrizacion" style="display: none; margin-top: 10px; padding: 15px; background: #F0F4F8; border: 2px solid #3498DB; border-radius: 8px; max-height: 400px; overflow-y: auto;">
            <div style="font-weight: bold; color: #2C3E50; margin-bottom: 12px; font-size: 14px; border-bottom: 2px solid #3498DB; padding-bottom: 8px;">
                ⚙️ Parámetros de Cálculo
            </div>
            
            <!-- EFICIENCIAS -->
            <div style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #E74C3C; font-size: 12px; margin-bottom: 8px; background: #FADBD8; padding: 4px 8px; border-radius: 4px;">
                    🔧 Eficiencias de Turbinas (η)
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 11px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Francis:</span>
                        <input type="number" id="param-ef-francis" value="0.92" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>PAT:</span>
                        <input type="number" id="param-ef-pat" value="0.86" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Pelton:</span>
                        <input type="number" id="param-ef-pelton" value="0.90" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Kaplan:</span>
                        <input type="number" id="param-ef-kaplan" value="0.89" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Low Head:</span>
                        <input type="number" id="param-ef-lowhead" value="0.89" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Turgo:</span>
                        <input type="number" id="param-ef-turgo" value="0.87" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Cross Flow:</span>
                        <input type="number" id="param-ef-crossflow" value="0.70" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                </div>
            </div>
            
            <!-- COSTOS CAPEX -->
            <div style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #27AE60; font-size: 12px; margin-bottom: 8px; background: #D5F5E3; padding: 4px 8px; border-radius: 4px;">
                    💰 Costos CAPEX (USD/kW)
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 11px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Francis:</span>
                        <input type="number" id="param-capex-francis" value="595" step="1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>PAT:</span>
                        <input type="number" id="param-capex-pat" value="100" step="1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Pelton:</span>
                        <input type="number" id="param-capex-pelton" value="300" step="1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Kaplan:</span>
                        <input type="number" id="param-capex-kaplan" value="425" step="1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Low Head:</span>
                        <input type="number" id="param-capex-lowhead" value="425" step="1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Turgo:</span>
                        <input type="number" id="param-capex-turgo" value="295" step="1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Cross Flow:</span>
                        <input type="number" id="param-capex-crossflow" value="200" step="1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                </div>
            </div>
            
            <!-- % INSTALACIÓN -->
            <div style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #8E44AD; font-size: 12px; margin-bottom: 8px; background: #E8DAEF; padding: 4px 8px; border-radius: 4px;">
                    🔩 % Instalación (Complejidad)
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 11px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Francis:</span>
                        <input type="number" id="param-inst-francis" value="0.20" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>PAT:</span>
                        <input type="number" id="param-inst-pat" value="0.10" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Pelton:</span>
                        <input type="number" id="param-inst-pelton" value="0.20" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Kaplan:</span>
                        <input type="number" id="param-inst-kaplan" value="0.20" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Low Head:</span>
                        <input type="number" id="param-inst-lowhead" value="0.20" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Turgo:</span>
                        <input type="number" id="param-inst-turgo" value="0.20" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Cross Flow:</span>
                        <input type="number" id="param-inst-crossflow" value="0.15" step="0.01" min="0" max="1" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                </div>
            </div>
            
            <!-- MULTIPLICADOR IMPACTO AMBIENTAL -->
            <div style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #16A085; font-size: 12px; margin-bottom: 8px; background: #D1F2EB; padding: 4px 8px; border-radius: 4px;">
                    🌿 Multiplicador Impacto Ambiental
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 11px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Francis:</span>
                        <input type="number" id="param-imp-francis" value="1.3" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>PAT:</span>
                        <input type="number" id="param-imp-pat" value="0.8" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Pelton:</span>
                        <input type="number" id="param-imp-pelton" value="1.3" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Kaplan:</span>
                        <input type="number" id="param-imp-kaplan" value="1.3" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Low Head:</span>
                        <input type="number" id="param-imp-lowhead" value="1.3" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Turgo:</span>
                        <input type="number" id="param-imp-turgo" value="1.0" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Cross Flow:</span>
                        <input type="number" id="param-imp-crossflow" value="0.8" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                </div>
            </div>
            
            <!-- MULTIPLICADOR TRANSPORTE -->
            <div style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #D35400; font-size: 12px; margin-bottom: 8px; background: #FAE5D3; padding: 4px 8px; border-radius: 4px;">
                    🚚 Multiplicador Transporte
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 11px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Francis:</span>
                        <input type="number" id="param-trans-francis" value="5.0" step="0.5" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>PAT:</span>
                        <input type="number" id="param-trans-pat" value="2.0" step="0.5" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Pelton:</span>
                        <input type="number" id="param-trans-pelton" value="2.0" step="0.5" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Kaplan:</span>
                        <input type="number" id="param-trans-kaplan" value="5.0" step="0.5" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Low Head:</span>
                        <input type="number" id="param-trans-lowhead" value="5.0" step="0.5" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Turgo:</span>
                        <input type="number" id="param-trans-turgo" value="5.0" step="0.5" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Cross Flow:</span>
                        <input type="number" id="param-trans-crossflow" value="3.5" step="0.5" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                </div>
            </div>
            
            <!-- DIFICULTAD TURBINA -->
            <div style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #C0392B; font-size: 12px; margin-bottom: 8px; background: #F5B7B1; padding: 4px 8px; border-radius: 4px;">
                    ⚡ Dificultad de Turbina (1-3)
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px; font-size: 11px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Francis:</span>
                        <input type="number" id="param-dif-francis" value="3" step="1" min="1" max="3" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>PAT:</span>
                        <input type="number" id="param-dif-pat" value="1" step="1" min="1" max="3" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Pelton:</span>
                        <input type="number" id="param-dif-pelton" value="1" step="1" min="1" max="3" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Kaplan:</span>
                        <input type="number" id="param-dif-kaplan" value="3" step="1" min="1" max="3" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Low Head:</span>
                        <input type="number" id="param-dif-lowhead" value="3" step="1" min="1" max="3" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Turgo:</span>
                        <input type="number" id="param-dif-turgo" value="3" step="1" min="1" max="3" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Cross Flow:</span>
                        <input type="number" id="param-dif-crossflow" value="2" step="1" min="1" max="3" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                </div>
            </div>
            
            <!-- MULTIPLICADOR POR REGIÓN -->
            <div style="margin-bottom: 15px;">
                <div style="font-weight: bold; color: #2980B9; font-size: 12px; margin-bottom: 8px; background: #D4E6F1; padding: 4px 8px; border-radius: 4px;">
                    🗺️ Multiplicador por Región
                </div>
                <div style="display: grid; grid-template-columns: 1fr; gap: 6px; font-size: 11px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Pacífico:</span>
                        <input type="number" id="param-reg-pacifico" value="1.6" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Eje Cafetero – Antioquia:</span>
                        <input type="number" id="param-reg-eje" value="1.4" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Centro Sur:</span>
                        <input type="number" id="param-reg-centrosur" value="1.3" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Centro Oriente:</span>
                        <input type="number" id="param-reg-centrooriente" value="1.2" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Caribe:</span>
                        <input type="number" id="param-reg-caribe" value="1.0" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Llano:</span>
                        <input type="number" id="param-reg-llano" value="1.0" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: white; padding: 4px 8px; border-radius: 4px;">
                        <span>Sin dato:</span>
                        <input type="number" id="param-reg-sindato" value="1.2" step="0.1" min="0" style="width: 60px; padding: 2px; border: 1px solid #ccc; border-radius: 3px; text-align: center;">
                    </div>
                </div>
            </div>
            
            <!-- FÓRMULAS DE COSTES -->
            <div style="margin-bottom: 15px; border: 2px solid #E67E22; border-radius: 8px; padding: 10px; background: #FDF2E9;">
                <div style="font-weight: bold; color: #E67E22; font-size: 13px; margin-bottom: 10px; text-align: center;">
                    📐 Fórmulas de Costes
                </div>
                
                <!-- Equipos -->
                <div style="margin-bottom: 10px; background: white; padding: 8px; border-radius: 4px;">
                    <div style="font-size: 10px; color: #666; margin-bottom: 4px;">
                        <b>Equipos:</b> coste_equipos = coste_turbina × <span style="color: #E67E22;">coef</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 11px;">Coef. equipos:</span>
                        <input type="number" id="param-form-coef-equipos" value="0.8" step="0.05" min="0" max="2" style="width: 70px; padding: 3px; border: 1px solid #E67E22; border-radius: 3px; text-align: center;">
                    </div>
                </div>
                
                <!-- Obra Civil -->
                <div style="margin-bottom: 10px; background: white; padding: 8px; border-radius: 4px;">
                    <div style="font-size: 10px; color: #666; margin-bottom: 4px;">
                        <b>Obra Civil:</b> coste = <span style="color: #E67E22;">Cbase</span> × potencia_kW
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 11px;">Cbase (USD/kW):</span>
                        <input type="number" id="param-form-cbase-obra" value="2200" step="100" min="0" style="width: 70px; padding: 3px; border: 1px solid #E67E22; border-radius: 3px; text-align: center;">
                    </div>
                </div>
                
                <!-- Línea Eléctrica -->
                <div style="margin-bottom: 10px; background: white; padding: 8px; border-radius: 4px;">
                    <div style="font-size: 10px; color: #666; margin-bottom: 4px;">
                        <b>Línea Eléctrica:</b> coste = <span style="color: #E67E22;">Cbase</span> + (kW × <span style="color: #E67E22;">F</span>)
                    </div>
                    <div style="font-size: 9px; color: #888; margin-bottom: 4px;">Si potencia &lt; 50 kW:</div>
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                        <span style="font-size: 10px;">Cbase:</span>
                        <input type="number" id="param-form-cbase-linea-baja" value="15000" step="1000" min="0" style="width: 65px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                        <span style="font-size: 10px;">F:</span>
                        <input type="number" id="param-form-f-linea-baja" value="400" step="50" min="0" style="width: 55px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                    </div>
                    <div style="font-size: 9px; color: #888; margin-bottom: 4px;">Si potencia ≥ 50 kW:</div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 10px;">Cbase:</span>
                        <input type="number" id="param-form-cbase-linea-alta" value="20000" step="1000" min="0" style="width: 65px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                        <span style="font-size: 10px;">F:</span>
                        <input type="number" id="param-form-f-linea-alta" value="500" step="50" min="0" style="width: 55px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                    </div>
                </div>
                
                <!-- Ambiental -->
                <div style="margin-bottom: 10px; background: white; padding: 8px; border-radius: 4px;">
                    <div style="font-size: 10px; color: #666; margin-bottom: 4px;">
                        <b>Ambiental:</b> coste = (<span style="color: #E67E22;">base</span> + <span style="color: #E67E22;">coef</span> × kW) × M_impacto
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 10px;">Base:</span>
                        <input type="number" id="param-form-base-ambiental" value="8000" step="500" min="0" style="width: 60px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                        <span style="font-size: 10px;">Coef/kW:</span>
                        <input type="number" id="param-form-coef-ambiental" value="100" step="10" min="0" style="width: 55px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                    </div>
                </div>
                
                <!-- Transporte -->
                <div style="margin-bottom: 10px; background: white; padding: 8px; border-radius: 4px;">
                    <div style="font-size: 10px; color: #666; margin-bottom: 4px;">
                        <b>Transporte:</b> D_real = dist × <span style="color: #E67E22;">factor_topo</span>
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px;">
                        <div style="display: flex; align-items: center; gap: 4px;">
                            <span style="font-size: 10px;">Factor topo:</span>
                            <input type="number" id="param-form-factor-topo" value="1.8" step="0.1" min="1" style="width: 50px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                        </div>
                        <div style="display: flex; align-items: center; gap: 4px;">
                            <span style="font-size: 10px;">Coef base:</span>
                            <input type="number" id="param-form-coef-transp-base" value="8.0" step="0.5" min="0" style="width: 50px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                        </div>
                    </div>
                    <div style="font-size: 9px; color: #888; margin-bottom: 2px;">Peso (ton) = kW × coef:</div>
                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                        <span style="font-size: 10px;">&lt;50kW:</span>
                        <input type="number" id="param-form-peso-bajo" value="0.150" step="0.01" min="0" style="width: 55px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                        <span style="font-size: 10px;">≥50kW:</span>
                        <input type="number" id="param-form-peso-alto" value="0.120" step="0.01" min="0" style="width: 55px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 10px;">Movilización:</span>
                        <input type="number" id="param-form-coef-movil" value="3000" step="500" min="0" style="width: 55px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                        <span style="font-size: 10px;">Logística:</span>
                        <input type="number" id="param-form-coef-logist" value="100" step="10" min="0" style="width: 50px; padding: 2px; border: 1px solid #E67E22; border-radius: 3px; text-align: center; font-size: 10px;">
                    </div>
                </div>
                
                <!-- Otros Costes -->
                <div style="margin-bottom: 10px; background: white; padding: 8px; border-radius: 4px;">
                    <div style="font-size: 10px; color: #666; margin-bottom: 4px;">
                        <b>Otros Costes:</b> otros = suma_parcial × <span style="color: #E67E22;">coef</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 11px;">Coef. otros (%):</span>
                        <input type="number" id="param-form-coef-otros" value="0.05" step="0.01" min="0" max="1" style="width: 70px; padding: 3px; border: 1px solid #E67E22; border-radius: 3px; text-align: center;">
                        <span style="font-size: 10px; color: #888;">(5%)</span>
                    </div>
                </div>
                
                <!-- OPEX -->
                <div style="background: white; padding: 8px; border-radius: 4px;">
                    <div style="font-size: 10px; color: #666; margin-bottom: 4px;">
                        <b>OPEX Anual:</b> opex = CAPEX × <span style="color: #E67E22;">coef</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 11px;">Coef. OPEX (%):</span>
                        <input type="number" id="param-form-coef-opex" value="0.03" step="0.01" min="0" max="1" style="width: 70px; padding: 3px; border: 1px solid #E67E22; border-radius: 3px; text-align: center;">
                        <span style="font-size: 10px; color: #888;">(3%)</span>
                    </div>
                </div>
            </div>
            
            <!-- BOTONES DE ACCIÓN -->
            <div style="display: flex; gap: 8px; margin-top: 15px;">
                <button onclick="aplicarParametros()" style="flex: 1; padding: 10px; background: #27AE60; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px;">
                    ✓ Aplicar y Recalcular
                </button>
                <button onclick="resetearParametros()" style="flex: 1; padding: 10px; background: #95A5A6; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px;">
                    🔄 Valores por Defecto
                </button>
            </div>
        </div>
        </div>
    </div>
    
    <!-- LEYENDA -->
    <div id="leyenda-mapa" style="position: fixed; top: 80px; right: 10px; background: white; z-index: 9998; padding: 12px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; max-width: 200px; margin-top: 320px;">
        
        <div style="font-weight: bold; color: #333; margin-bottom: 10px; border-bottom: 2px solid #E54D9A; padding-bottom: 6px; font-size: 12px;">
            📍 Leyenda
        </div>
        
        <!-- PUNTOS -->
        <div style="margin-bottom: 12px;">
            <div style="font-weight: 600; color: #555; margin-bottom: 6px; font-size: 10px;">PUNTOS</div>
            <div style="display: flex; align-items: center; margin-bottom: 4px;">
                <div style="width: 12px; height: 12px; background: #00FF00; border-radius: 50%; margin-right: 8px; border: 2px solid #00CC00;"></div>
                <span>Puntos mostrados</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: 12px; height: 12px; background: #f5576c; border-radius: 50%; margin-right: 8px; border: 2px solid #e63950;"></div>
                <span>Puntos priorizados</span>
            </div>
        </div>
        
        <!-- ÁREAS PROTEGIDAS -->
        <div>
            <div style="font-weight: 600; color: #555; margin-bottom: 6px; font-size: 10px;">ÁREAS Y TERRITORIOS</div>
            
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: 16px; height: 10px; background: #8B4513; margin-right: 8px; border-radius: 2px; opacity: 0.7;"></div>
                <span>Tierras Com. Negras</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: 16px; height: 10px; background: #FF8C00; margin-right: 8px; border-radius: 2px; opacity: 0.7;"></div>
                <span>Resguardos Indígenas</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: 16px; height: 10px; background: #DAA520; margin-right: 8px; border-radius: 2px; opacity: 0.7;"></div>
                <span>Parques Arqueológicos 🚫</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: 16px; height: 10px; background: #87CEEB; margin-right: 8px; border-radius: 2px; opacity: 0.7;"></div>
                <span>Complejos de Páramo</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: 16px; height: 10px; background: #90EE90; margin-right: 8px; border-radius: 2px; opacity: 0.7;"></div>
                <span>Áreas Protección Local</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: 16px; height: 10px; background: #3CB371; margin-right: 8px; border-radius: 2px; opacity: 0.7;"></div>
                <span>Áreas Protección Regional</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: 16px; height: 10px; background: #228B22; margin-right: 8px; border-radius: 2px; opacity: 0.7;"></div>
                <span>Reservas Naturales (RNSC)</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: 16px; height: 10px; background: #006400; margin-right: 8px; border-radius: 2px; opacity: 0.7;"></div>
                <span>Áreas Protegidas (RUNAP)</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <div style="width: 16px; height: 10px; background: #004d00; margin-right: 8px; border-radius: 2px; opacity: 0.7;"></div>
                <span>Parques Nacionales 🚫</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: 16px; height: 10px; background: #2F4F4F; margin-right: 8px; border-radius: 2px; opacity: 0.7;"></div>
                <span>Reservas Forestales</span>
            </div>
        </div>
        
        <!-- NOTA -->
        <div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 9px; color: #888;">
            🚫 = Áreas restrictivas (excluyen puntos)
        </div>
    </div>
    
    <!-- MODAL ANÁLISIS MULTIESCENARIO -->
    <div id="modal-multiescenario" class="modal-multiescenario">
        <div class="modal-contenido">
            <div class="modal-header">
                <h2 style="margin: 0; color: #2C3E50; font-size: 20px;">📊 Análisis Multiescenario - VSS vs CAPEX Acumulado</h2>
                <span class="modal-cerrar" onclick="cerrarModalMultiescenario()">&times;</span>
            </div>
            
            <div style="margin-bottom: 15px; padding: 12px; background: #E8F6F3; border-radius: 8px; border-left: 4px solid #1ABC9C;">
                <p style="margin: 0; font-size: 12px; color: #1E8449;">
                    <strong>📈 Interpretación:</strong> Esta gráfica muestra cómo crecen las VSS abastecidas y el CAPEX total acumulado 
                    a medida que se añaden puntos según el ranking de priorización (de mejor a peor). 
                    Cada punto representa un proyecto adicional incorporado al portafolio.
                </p>
            </div>
            
            <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                <div style="flex: 1; padding: 15px; background: #F8F9FA; border-radius: 8px; text-align: center;">
                    <div style="font-size: 11px; color: #666; margin-bottom: 5px;">Total Puntos Priorizados</div>
                    <div id="stat-total-puntos" style="font-size: 24px; font-weight: bold; color: #3498DB;">0</div>
                </div>
                <div style="flex: 1; padding: 15px; background: #F8F9FA; border-radius: 8px; text-align: center;">
                    <div style="font-size: 11px; color: #666; margin-bottom: 5px;">VSS Totales Abastecibles</div>
                    <div id="stat-total-vss" style="font-size: 24px; font-weight: bold; color: #27AE60;">0</div>
                </div>
                <div style="flex: 1; padding: 15px; background: #F8F9FA; border-radius: 8px; text-align: center;">
                    <div style="font-size: 11px; color: #666; margin-bottom: 5px;">CAPEX Total (USD)</div>
                    <div id="stat-total-capex" style="font-size: 24px; font-weight: bold; color: #E74C3C;">$0</div>
                </div>
                <div style="flex: 1; padding: 15px; background: #F8F9FA; border-radius: 8px; text-align: center;">
                    <div style="font-size: 11px; color: #666; margin-bottom: 5px;">Costo Promedio/VSS</div>
                    <div id="stat-costo-vss" style="font-size: 24px; font-weight: bold; color: #9B59B6;">$0</div>
                </div>
            </div>
            
            <div style="height: 450px; position: relative;">
                <canvas id="grafica-multiescenario"></canvas>
            </div>
            
            <div style="margin-top: 15px; padding: 12px; background: #FDF2E9; border-radius: 8px; border-left: 4px solid #E67E22;">
                <p style="margin: 0; font-size: 11px; color: #935116;">
                    <strong>💡 Nota:</strong> Use esta gráfica para identificar el punto óptimo de inversión según su presupuesto disponible.
                    Puede establecer un presupuesto máximo en los filtros de priorización para visualizar solo los proyectos dentro de ese límite.
                </p>
            </div>
        </div>
    </div>
    
    <style>
        input[type="range"] {{
            -webkit-appearance: none;
            appearance: none;
            background: #ddd;
            outline: none;
            border-radius: 3px;
        }}
        input[type="range"]::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 18px;
            height: 18px;
            background: #E54D9A;
            cursor: pointer;
            border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        input[type="range"]::-moz-range-thumb {{
            width: 18px;
            height: 18px;
            background: #E54D9A;
            cursor: pointer;
            border-radius: 50%;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        /* Modal de Análisis Multiescenario */
        .modal-multiescenario {{
            display: none;
            position: fixed;
            z-index: 10000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.7);
        }}
        .modal-contenido {{
            background-color: white;
            margin: 3% auto;
            padding: 25px;
            border-radius: 12px;
            width: 85%;
            max-width: 1000px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 5px 30px rgba(0,0,0,0.3);
        }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #3498DB;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .modal-cerrar {{
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            color: #666;
            transition: color 0.3s;
        }}
        .modal-cerrar:hover {{
            color: #E74C3C;
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    '''
    
    # JavaScript
    javascript = f'''
    <script>
    var puntos = {json.dumps(puntos_data)};
    var puntosOriginal = JSON.parse(JSON.stringify(puntos)); // Copia de seguridad de datos originales
    var layer = null;
    var modoPriorizacion = false;
    var rankingPuntos = [];
    var puntosPriorizadosCompletos = []; // Almacenar todos los puntos priorizados
    var totalPuntosPriorizados = 0; // Total de puntos para calcular colores
    
    // Función para calcular color según ranking (escala de azules)
    // Mejor ranking = Azul oscuro, peor ranking = Azul claro
    function getColorPorRanking(ranking, totalPuntos) {{
        if (totalPuntos <= 1) return '#0D3B66'; // Azul oscuro si solo hay un punto
        
        // Normalizar ranking a valor entre 0 y 1
        // ranking 1 (mejor) → t = 0 → azul oscuro
        // ranking máximo (peor) → t = 1 → azul claro
        var t = (ranking - 1) / (totalPuntos - 1);
        
        // Colores de la escala de azules
        // Azul oscuro (mejor): RGB(13, 59, 102) = #0D3B66
        // Azul claro (peor): RGB(173, 216, 230) = #ADD8E6
        var r1 = 13, g1 = 59, b1 = 102;    // Azul oscuro
        var r2 = 173, g2 = 216, b2 = 230;  // Azul claro
        
        // Interpolación lineal
        var r = Math.round(r1 + t * (r2 - r1));
        var g = Math.round(g1 + t * (g2 - g1));
        var b = Math.round(b1 + t * (b2 - b1));
        
        return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();
    }}
    
    // PARÁMETROS EDITABLES
    var PARAM_EFICIENCIAS = {{
        'Francis': 0.92, 'PAT': 0.86, 'Pelton': 0.90, 'Kaplan': 0.89,
        'Low Head': 0.89, 'Turgo': 0.87, 'Cross Flow': 0.70
    }};
    var PARAM_COSTOS_CAPEX = {{
        'Francis': 595, 'PAT': 100, 'Pelton': 300, 'Kaplan': 425,
        'Low Head': 425, 'Turgo': 295, 'Cross Flow': 200
    }};
    var PARAM_COMPLEJIDAD = {{
        'Francis': 0.20, 'PAT': 0.10, 'Pelton': 0.20, 'Kaplan': 0.20,
        'Low Head': 0.20, 'Turgo': 0.20, 'Cross Flow': 0.15
    }};
    var PARAM_IMPACTO = {{
        'Francis': 1.3, 'PAT': 0.8, 'Pelton': 1.3, 'Kaplan': 1.3,
        'Low Head': 1.3, 'Turgo': 1.0, 'Cross Flow': 0.8
    }};
    var PARAM_TRANSPORTE = {{
        'Francis': 5.0, 'PAT': 2.0, 'Pelton': 2.0, 'Kaplan': 5.0,
        'Low Head': 5.0, 'Turgo': 5.0, 'Cross Flow': 3.5
    }};
    var PARAM_DIFICULTAD = {{
        'Francis': 3, 'PAT': 1, 'Pelton': 1, 'Kaplan': 3,
        'Low Head': 3, 'Turgo': 3, 'Cross Flow': 2
    }};
    var PARAM_REGION = {{
        'Región Pacífico': 1.6,
        'Región Eje Cafetero – Antioquia': 1.4,
        'Región Centro Sur': 1.3,
        'Región Centro Oriente': 1.2,
        'Región Caribe': 1.0,
        'Región Llano': 1.0,
        '': 1.2
    }};
    
    // PARÁMETROS DE FÓRMULAS DE COSTES
    var PARAM_FORMULAS = {{
        // Equipos
        coef_equipos: 0.8,              // coste_equipos = coste_turbina * coef_equipos
        
        // Obra civil
        Cbase_obra_civil: 2200,         // coste_obra_civil = Cbase * potencia_kw
        
        // Línea eléctrica (potencia < 50 kW)
        Cbase_linea_baja: 15000,
        F_linea_baja: 400,
        // Línea eléctrica (potencia >= 50 kW)
        Cbase_linea_alta: 20000,
        F_linea_alta: 500,
        
        // Ambiental
        base_ambiental: 8000,           // coste_ambiental = (base + coef*kW) * M_impacto
        coef_ambiental_kw: 100,
        
        // Transporte
        factor_topografia: 1.8,         // D_real = distancia * factor
        peso_kw_bajo: 0.150,            // peso (ton) = kW * coef (si kW < 50)
        peso_kw_alto: 0.120,            // peso (ton) = kW * coef (si kW >= 50)
        coef_transporte_base: 8.0,      // coste_base = coef * D * W * M_turb * M_region
        coef_movilizacion: 3000,        // C_movilizacion = coef * dificultad * M_region
        coef_logistica: 100,            // C_logistica = coef * kW * M_region
        
        // Otros costes
        coef_otros_costes: 0.05,        // otros_costes = suma_parcial * coef
        
        // OPEX
        coef_opex: 0.03                  // opex = CAPEX * coef
    }};
    
    // Función para mostrar/ocultar panel de parametrización
    function toggleParametrizacion() {{
        var panel = document.getElementById('panel-parametrizacion');
        if (panel.style.display === 'none') {{
            panel.style.display = 'block';
        }} else {{
            panel.style.display = 'none';
        }}
    }}
    
    // Función para minimizar/maximizar el panel de filtros
    function toggleMinimizar() {{
        var contenido = document.getElementById('panel-contenido');
        var btn = document.getElementById('btn-minimizar');
        var panel = document.getElementById('control-panel');
        
        if (contenido.style.display === 'none') {{
            contenido.style.display = 'block';
            btn.textContent = '−';
            btn.title = 'Minimizar';
            panel.style.width = '380px';
        }} else {{
            contenido.style.display = 'none';
            btn.textContent = '+';
            btn.title = 'Maximizar';
            panel.style.width = 'auto';
        }}
    }}
    
    // Función para leer parámetros del formulario
    function leerParametrosDelFormulario() {{
        // Eficiencias
        PARAM_EFICIENCIAS['Francis'] = parseFloat(document.getElementById('param-ef-francis').value) || 0.92;
        PARAM_EFICIENCIAS['PAT'] = parseFloat(document.getElementById('param-ef-pat').value) || 0.86;
        PARAM_EFICIENCIAS['Pelton'] = parseFloat(document.getElementById('param-ef-pelton').value) || 0.90;
        PARAM_EFICIENCIAS['Kaplan'] = parseFloat(document.getElementById('param-ef-kaplan').value) || 0.89;
        PARAM_EFICIENCIAS['Low Head'] = parseFloat(document.getElementById('param-ef-lowhead').value) || 0.89;
        PARAM_EFICIENCIAS['Turgo'] = parseFloat(document.getElementById('param-ef-turgo').value) || 0.87;
        PARAM_EFICIENCIAS['Cross Flow'] = parseFloat(document.getElementById('param-ef-crossflow').value) || 0.70;
        
        // Costos CAPEX
        PARAM_COSTOS_CAPEX['Francis'] = parseFloat(document.getElementById('param-capex-francis').value) || 595;
        PARAM_COSTOS_CAPEX['PAT'] = parseFloat(document.getElementById('param-capex-pat').value) || 100;
        PARAM_COSTOS_CAPEX['Pelton'] = parseFloat(document.getElementById('param-capex-pelton').value) || 300;
        PARAM_COSTOS_CAPEX['Kaplan'] = parseFloat(document.getElementById('param-capex-kaplan').value) || 425;
        PARAM_COSTOS_CAPEX['Low Head'] = parseFloat(document.getElementById('param-capex-lowhead').value) || 425;
        PARAM_COSTOS_CAPEX['Turgo'] = parseFloat(document.getElementById('param-capex-turgo').value) || 295;
        PARAM_COSTOS_CAPEX['Cross Flow'] = parseFloat(document.getElementById('param-capex-crossflow').value) || 200;
        
        // Complejidad instalación
        PARAM_COMPLEJIDAD['Francis'] = parseFloat(document.getElementById('param-inst-francis').value) || 0.20;
        PARAM_COMPLEJIDAD['PAT'] = parseFloat(document.getElementById('param-inst-pat').value) || 0.10;
        PARAM_COMPLEJIDAD['Pelton'] = parseFloat(document.getElementById('param-inst-pelton').value) || 0.20;
        PARAM_COMPLEJIDAD['Kaplan'] = parseFloat(document.getElementById('param-inst-kaplan').value) || 0.20;
        PARAM_COMPLEJIDAD['Low Head'] = parseFloat(document.getElementById('param-inst-lowhead').value) || 0.20;
        PARAM_COMPLEJIDAD['Turgo'] = parseFloat(document.getElementById('param-inst-turgo').value) || 0.20;
        PARAM_COMPLEJIDAD['Cross Flow'] = parseFloat(document.getElementById('param-inst-crossflow').value) || 0.15;
        
        // Impacto ambiental
        PARAM_IMPACTO['Francis'] = parseFloat(document.getElementById('param-imp-francis').value) || 1.3;
        PARAM_IMPACTO['PAT'] = parseFloat(document.getElementById('param-imp-pat').value) || 0.8;
        PARAM_IMPACTO['Pelton'] = parseFloat(document.getElementById('param-imp-pelton').value) || 1.3;
        PARAM_IMPACTO['Kaplan'] = parseFloat(document.getElementById('param-imp-kaplan').value) || 1.3;
        PARAM_IMPACTO['Low Head'] = parseFloat(document.getElementById('param-imp-lowhead').value) || 1.3;
        PARAM_IMPACTO['Turgo'] = parseFloat(document.getElementById('param-imp-turgo').value) || 1.0;
        PARAM_IMPACTO['Cross Flow'] = parseFloat(document.getElementById('param-imp-crossflow').value) || 0.8;
        
        // Transporte
        PARAM_TRANSPORTE['Francis'] = parseFloat(document.getElementById('param-trans-francis').value) || 5.0;
        PARAM_TRANSPORTE['PAT'] = parseFloat(document.getElementById('param-trans-pat').value) || 2.0;
        PARAM_TRANSPORTE['Pelton'] = parseFloat(document.getElementById('param-trans-pelton').value) || 2.0;
        PARAM_TRANSPORTE['Kaplan'] = parseFloat(document.getElementById('param-trans-kaplan').value) || 5.0;
        PARAM_TRANSPORTE['Low Head'] = parseFloat(document.getElementById('param-trans-lowhead').value) || 5.0;
        PARAM_TRANSPORTE['Turgo'] = parseFloat(document.getElementById('param-trans-turgo').value) || 5.0;
        PARAM_TRANSPORTE['Cross Flow'] = parseFloat(document.getElementById('param-trans-crossflow').value) || 3.5;
        
        // Dificultad
        PARAM_DIFICULTAD['Francis'] = parseInt(document.getElementById('param-dif-francis').value) || 3;
        PARAM_DIFICULTAD['PAT'] = parseInt(document.getElementById('param-dif-pat').value) || 1;
        PARAM_DIFICULTAD['Pelton'] = parseInt(document.getElementById('param-dif-pelton').value) || 1;
        PARAM_DIFICULTAD['Kaplan'] = parseInt(document.getElementById('param-dif-kaplan').value) || 3;
        PARAM_DIFICULTAD['Low Head'] = parseInt(document.getElementById('param-dif-lowhead').value) || 3;
        PARAM_DIFICULTAD['Turgo'] = parseInt(document.getElementById('param-dif-turgo').value) || 3;
        PARAM_DIFICULTAD['Cross Flow'] = parseInt(document.getElementById('param-dif-crossflow').value) || 2;
        
        // Regiones
        PARAM_REGION['Región Pacífico'] = parseFloat(document.getElementById('param-reg-pacifico').value) || 1.6;
        PARAM_REGION['Región Eje Cafetero – Antioquia'] = parseFloat(document.getElementById('param-reg-eje').value) || 1.4;
        PARAM_REGION['Región Centro Sur'] = parseFloat(document.getElementById('param-reg-centrosur').value) || 1.3;
        PARAM_REGION['Región Centro Oriente'] = parseFloat(document.getElementById('param-reg-centrooriente').value) || 1.2;
        PARAM_REGION['Región Caribe'] = parseFloat(document.getElementById('param-reg-caribe').value) || 1.0;
        PARAM_REGION['Región Llano'] = parseFloat(document.getElementById('param-reg-llano').value) || 1.0;
        PARAM_REGION[''] = parseFloat(document.getElementById('param-reg-sindato').value) || 1.2;
        
        // Fórmulas de costes
        PARAM_FORMULAS.coef_equipos = parseFloat(document.getElementById('param-form-coef-equipos').value) || 0.8;
        PARAM_FORMULAS.Cbase_obra_civil = parseFloat(document.getElementById('param-form-cbase-obra').value) || 2200;
        PARAM_FORMULAS.Cbase_linea_baja = parseFloat(document.getElementById('param-form-cbase-linea-baja').value) || 15000;
        PARAM_FORMULAS.F_linea_baja = parseFloat(document.getElementById('param-form-f-linea-baja').value) || 400;
        PARAM_FORMULAS.Cbase_linea_alta = parseFloat(document.getElementById('param-form-cbase-linea-alta').value) || 20000;
        PARAM_FORMULAS.F_linea_alta = parseFloat(document.getElementById('param-form-f-linea-alta').value) || 500;
        PARAM_FORMULAS.base_ambiental = parseFloat(document.getElementById('param-form-base-ambiental').value) || 8000;
        PARAM_FORMULAS.coef_ambiental_kw = parseFloat(document.getElementById('param-form-coef-ambiental').value) || 100;
        PARAM_FORMULAS.factor_topografia = parseFloat(document.getElementById('param-form-factor-topo').value) || 1.8;
        PARAM_FORMULAS.peso_kw_bajo = parseFloat(document.getElementById('param-form-peso-bajo').value) || 0.150;
        PARAM_FORMULAS.peso_kw_alto = parseFloat(document.getElementById('param-form-peso-alto').value) || 0.120;
        PARAM_FORMULAS.coef_transporte_base = parseFloat(document.getElementById('param-form-coef-transp-base').value) || 8.0;
        PARAM_FORMULAS.coef_movilizacion = parseFloat(document.getElementById('param-form-coef-movil').value) || 3000;
        PARAM_FORMULAS.coef_logistica = parseFloat(document.getElementById('param-form-coef-logist').value) || 100;
        PARAM_FORMULAS.coef_otros_costes = parseFloat(document.getElementById('param-form-coef-otros').value) || 0.05;
        PARAM_FORMULAS.coef_opex = parseFloat(document.getElementById('param-form-coef-opex').value) || 0.03;
    }}
    
    // Función para calcular costes detallados de una turbina
    function calcularCostesDetallados(tipoTurbina, potenciaKw, caidaM, distCapitalM, region) {{
        var costes = {{}};
        
        // 1. Coste turbina
        var costeTurbina = potenciaKw * PARAM_COSTOS_CAPEX[tipoTurbina];
        costes.coste_turbina = costeTurbina;
        
        // 2. Coste equipos sin turbina
        var costeEquipos = costeTurbina * PARAM_FORMULAS.coef_equipos;
        costes.coste_equipos = costeEquipos;
        
        // 3. Coste obra civil
        var Cbase = PARAM_FORMULAS.Cbase_obra_civil;
        var costeObraCivil = Cbase * potenciaKw;
        costes.coste_obra_civil = costeObraCivil;
        
        // 4. Costes instalación
        var complejidad = PARAM_COMPLEJIDAD[tipoTurbina];
        var costeInstalacion = (costeEquipos + costeTurbina) * complejidad;
        costes.coste_instalacion = costeInstalacion;
        
        // 5. Coste línea eléctrica
        var CbaseLinea, F;
        if (potenciaKw < 50) {{
            CbaseLinea = PARAM_FORMULAS.Cbase_linea_baja;
            F = PARAM_FORMULAS.F_linea_baja;
        }} else {{
            CbaseLinea = PARAM_FORMULAS.Cbase_linea_alta;
            F = PARAM_FORMULAS.F_linea_alta;
        }}
        var costeLinea = CbaseLinea + (potenciaKw * F);
        costes.coste_linea = costeLinea;
        
        // 6. Costes ambientales
        var mImpacto = PARAM_IMPACTO[tipoTurbina];
        var costeAmbiental = (PARAM_FORMULAS.base_ambiental + PARAM_FORMULAS.coef_ambiental_kw * potenciaKw) * mImpacto;
        costes.coste_ambiental = costeAmbiental;
        
        // 7. Coste transporte
        var distCapitalKm = distCapitalM / 1000;
        var dReal = distCapitalKm * PARAM_FORMULAS.factor_topografia;
        
        var W;
        if (potenciaKw < 50) {{
            W = potenciaKw * PARAM_FORMULAS.peso_kw_bajo;
        }} else {{
            W = potenciaKw * PARAM_FORMULAS.peso_kw_alto;
        }}
        
        var mTurb = PARAM_TRANSPORTE[tipoTurbina];
        var mRegion = PARAM_REGION[region] || 1.2;
        
        var costeTransporteBase = PARAM_FORMULAS.coef_transporte_base * dReal * W * mTurb * mRegion;
        
        var dificultadTurb = PARAM_DIFICULTAD[tipoTurbina];
        var cMovilizacion = PARAM_FORMULAS.coef_movilizacion * dificultadTurb * mRegion;
        var cLogistica = PARAM_FORMULAS.coef_logistica * potenciaKw * mRegion;
        
        var costeTransporte = costeTransporteBase + cMovilizacion + cLogistica;
        costes.coste_transporte = costeTransporte;
        
        // 8. Otros costes
        var sumaParcial = costeTurbina + costeEquipos + costeObraCivil + 
                          costeInstalacion + costeLinea + costeAmbiental + costeTransporte;
        var otrosCostes = sumaParcial * PARAM_FORMULAS.coef_otros_costes;
        costes.otros_costes = otrosCostes;
        
        // CAPEX Total
        var capexTotal = sumaParcial + otrosCostes;
        costes.capex_total = capexTotal;
        
        // OPEX
        var opex = capexTotal * PARAM_FORMULAS.coef_opex;
        costes.opex = opex;
        
        return costes;
    }}
    
    // Función para determinar turbinas aplicables
    function determinarTurbinasAplicables(caudalCfs, caidaFt) {{
        var turbinasAplicables = [];
        
        // Definir polígonos simplificados
        // Low Head: caudal 1-10000, caida 1-20
        if (caudalCfs >= 1 && caudalCfs <= 10000 && caidaFt >= 1 && caidaFt <= 20) {{
            turbinasAplicables.push('Low Head');
        }}
        // PAT: caudal 1-30, caida 30-300
        if (caudalCfs >= 1 && caudalCfs <= 30 && caidaFt >= 30 && caidaFt <= 300) {{
            turbinasAplicables.push('PAT');
        }}
        // Kaplan: caudal 100-10000, caida 10-150
        if (caudalCfs >= 100 && caudalCfs <= 10000 && caidaFt >= 10 && caidaFt <= 150) {{
            turbinasAplicables.push('Kaplan');
        }}
        // Cross Flow: caudal 1-200, caida 10-400
        if (caudalCfs >= 1 && caudalCfs <= 200 && caidaFt >= 10 && caidaFt <= 400) {{
            turbinasAplicables.push('Cross Flow');
        }}
        // Turgo: caudal 1-500, caida 100-1000
        if (caudalCfs >= 1 && caudalCfs <= 500 && caidaFt >= 100 && caidaFt <= 1000) {{
            turbinasAplicables.push('Turgo');
        }}
        // Francis: complejo, simplificado
        if ((caudalCfs >= 10 && caudalCfs <= 3000 && caidaFt >= 50 && caidaFt <= 300) ||
            (caudalCfs >= 10 && caudalCfs <= 200 && caidaFt >= 300 && caidaFt <= 3000)) {{
            turbinasAplicables.push('Francis');
        }}
        // Pelton: caudal 1-200, caida 300-5000
        if (caudalCfs >= 1 && caudalCfs <= 200 && caidaFt >= 300 && caidaFt <= 5000) {{
            turbinasAplicables.push('Pelton');
        }}
        
        return turbinasAplicables;
    }}
    
    // Función para recalcular todas las turbinas de un punto
    function recalcularTurbinasPunto(p) {{
        var turbinasAplicables = determinarTurbinasAplicables(p.caudal_cfs, p.caida_ft);
        var nuevasTurbinas = [];
        
        var potenciaAbastecerVss = p.vss * p.potencia_pico;
        
        turbinasAplicables.forEach(function(tipoTurbina) {{
            var eficiencia = PARAM_EFICIENCIAS[tipoTurbina];
            var potenciaMaxima = p.potencia_k * 0.9 * eficiencia;
            
            var potenciaParaCostes, vssAbastecibles, esHibrida;
            if (potenciaMaxima < potenciaAbastecerVss) {{
                potenciaParaCostes = potenciaMaxima;
                vssAbastecibles = Math.floor(potenciaMaxima / p.potencia_pico);
                esHibrida = true;
            }} else {{
                potenciaParaCostes = potenciaAbastecerVss;
                vssAbastecibles = Math.floor(p.vss);
                esHibrida = false;
            }}
            
            var costes = calcularCostesDetallados(
                tipoTurbina,
                potenciaParaCostes,
                p.caida,
                p.dist_punto_capital,
                p.region
            );
            
            var capexPorVss = vssAbastecibles > 0 ? costes.capex_total / vssAbastecibles : 0;
            
            nuevasTurbinas.push({{
                tipo: tipoTurbina,
                potencia_maxima: Math.round(potenciaMaxima * 100) / 100,
                potencia_abastecer_vss: Math.round(potenciaAbastecerVss * 100) / 100,
                potencia_usada_costes: Math.round(potenciaParaCostes * 100) / 100,
                vss_abastecibles: vssAbastecibles,
                es_hibrida: esHibrida,
                capex_simple: Math.round(potenciaMaxima * PARAM_COSTOS_CAPEX[tipoTurbina] * 100) / 100,
                coste_turbina: Math.round(costes.coste_turbina * 100) / 100,
                coste_equipos: Math.round(costes.coste_equipos * 100) / 100,
                coste_obra_civil: Math.round(costes.coste_obra_civil * 100) / 100,
                coste_instalacion: Math.round(costes.coste_instalacion * 100) / 100,
                coste_linea: Math.round(costes.coste_linea * 100) / 100,
                coste_ambiental: Math.round(costes.coste_ambiental * 100) / 100,
                coste_transporte: Math.round(costes.coste_transporte * 100) / 100,
                otros_costes: Math.round(costes.otros_costes * 100) / 100,
                capex_total: Math.round(costes.capex_total * 100) / 100,
                opex: Math.round(costes.opex * 100) / 100,
                capex_por_vss: Math.round(capexPorVss * 100) / 100
            }});
        }});
        
        return nuevasTurbinas;
    }}
    
    // Función para aplicar parámetros y recalcular todo
    function aplicarParametros() {{
        // Leer parámetros del formulario
        leerParametrosDelFormulario();
        
        // Recalcular turbinas para cada punto
        puntos.forEach(function(p) {{
            p.turbinas = recalcularTurbinasPunto(p);
        }});
        
        // Actualizar visualización
        actualizar();
        
        alert('✓ Parámetros aplicados\\n\\nSe han recalculado los costes de ' + puntos.length + ' puntos con los nuevos parámetros.');
    }}
    
    // Función para resetear parámetros a valores por defecto
    function resetearParametros() {{
        // Eficiencias
        document.getElementById('param-ef-francis').value = '0.92';
        document.getElementById('param-ef-pat').value = '0.86';
        document.getElementById('param-ef-pelton').value = '0.90';
        document.getElementById('param-ef-kaplan').value = '0.89';
        document.getElementById('param-ef-lowhead').value = '0.89';
        document.getElementById('param-ef-turgo').value = '0.87';
        document.getElementById('param-ef-crossflow').value = '0.70';
        
        // CAPEX
        document.getElementById('param-capex-francis').value = '595';
        document.getElementById('param-capex-pat').value = '100';
        document.getElementById('param-capex-pelton').value = '300';
        document.getElementById('param-capex-kaplan').value = '425';
        document.getElementById('param-capex-lowhead').value = '425';
        document.getElementById('param-capex-turgo').value = '295';
        document.getElementById('param-capex-crossflow').value = '200';
        
        // Instalación
        document.getElementById('param-inst-francis').value = '0.20';
        document.getElementById('param-inst-pat').value = '0.10';
        document.getElementById('param-inst-pelton').value = '0.20';
        document.getElementById('param-inst-kaplan').value = '0.20';
        document.getElementById('param-inst-lowhead').value = '0.20';
        document.getElementById('param-inst-turgo').value = '0.20';
        document.getElementById('param-inst-crossflow').value = '0.15';
        
        // Impacto
        document.getElementById('param-imp-francis').value = '1.3';
        document.getElementById('param-imp-pat').value = '0.8';
        document.getElementById('param-imp-pelton').value = '1.3';
        document.getElementById('param-imp-kaplan').value = '1.3';
        document.getElementById('param-imp-lowhead').value = '1.3';
        document.getElementById('param-imp-turgo').value = '1.0';
        document.getElementById('param-imp-crossflow').value = '0.8';
        
        // Transporte
        document.getElementById('param-trans-francis').value = '5.0';
        document.getElementById('param-trans-pat').value = '2.0';
        document.getElementById('param-trans-pelton').value = '2.0';
        document.getElementById('param-trans-kaplan').value = '5.0';
        document.getElementById('param-trans-lowhead').value = '5.0';
        document.getElementById('param-trans-turgo').value = '5.0';
        document.getElementById('param-trans-crossflow').value = '3.5';
        
        // Dificultad
        document.getElementById('param-dif-francis').value = '3';
        document.getElementById('param-dif-pat').value = '1';
        document.getElementById('param-dif-pelton').value = '1';
        document.getElementById('param-dif-kaplan').value = '3';
        document.getElementById('param-dif-lowhead').value = '3';
        document.getElementById('param-dif-turgo').value = '3';
        document.getElementById('param-dif-crossflow').value = '2';
        
        // Regiones
        document.getElementById('param-reg-pacifico').value = '1.6';
        document.getElementById('param-reg-eje').value = '1.4';
        document.getElementById('param-reg-centrosur').value = '1.3';
        document.getElementById('param-reg-centrooriente').value = '1.2';
        document.getElementById('param-reg-caribe').value = '1.0';
        document.getElementById('param-reg-llano').value = '1.0';
        document.getElementById('param-reg-sindato').value = '1.2';
        
        // Fórmulas de costes
        document.getElementById('param-form-coef-equipos').value = '0.8';
        document.getElementById('param-form-cbase-obra').value = '2200';
        document.getElementById('param-form-cbase-linea-baja').value = '15000';
        document.getElementById('param-form-f-linea-baja').value = '400';
        document.getElementById('param-form-cbase-linea-alta').value = '20000';
        document.getElementById('param-form-f-linea-alta').value = '500';
        document.getElementById('param-form-base-ambiental').value = '8000';
        document.getElementById('param-form-coef-ambiental').value = '100';
        document.getElementById('param-form-factor-topo').value = '1.8';
        document.getElementById('param-form-peso-bajo').value = '0.150';
        document.getElementById('param-form-peso-alto').value = '0.120';
        document.getElementById('param-form-coef-transp-base').value = '8.0';
        document.getElementById('param-form-coef-movil').value = '3000';
        document.getElementById('param-form-coef-logist').value = '100';
        document.getElementById('param-form-coef-otros').value = '0.05';
        document.getElementById('param-form-coef-opex').value = '0.03';
        
        alert('✓ Parámetros reseteados a valores por defecto\\n\\nHaz clic en "Aplicar y Recalcular" para actualizar los cálculos.');
    }}
    
    // Función para formatear números con espacios (23 000 en lugar de 23,000)
    function formatNumber(num) {{
        var numStr = Math.round(num).toString();
        var result = '';
        var cnt = 0;
        for (var i = numStr.length - 1; i >= 0; i--) {{
            result = numStr[i] + result;
            cnt++;
            if (cnt === 3 && i > 0) {{
                result = ' ' + result;
                cnt = 0;
            }}
        }}
        return result;
    }}
    
    // Función para descargar informe Word del punto
    function descargarInforme(puntoId, tasaCambio, ranking) {{
        var punto = puntos.find(function(p) {{ return p.id === puntoId; }});
        if (!punto) {{
            alert('Error: No se encontró el punto');
            return;
        }}
        
        var fechaGeneracion = new Date().toLocaleString('es-ES');
        
        // Estilos basados en la plantilla corporativa
        var html = '<!DOCTYPE html><html><head><meta charset="UTF-8">';
        html += '<style>';
        html += 'body {{ font-family: Calibri, Arial, sans-serif; margin: 30px; font-size: 11pt; }}';
        html += 'h1 {{ text-align: center; font-size: 14pt; font-weight: normal; margin-bottom: 20px; }}';
        html += 'table {{ border-collapse: collapse; width: 100%; margin-bottom: 15px; }}';
        html += 'td, th {{ border: 1px solid #ccc; padding: 6px 10px; font-size: 10pt; }}';
        html += '.header-rosa {{ background: #ED1782; color: white; text-align: center; font-weight: bold; }}';
        html += '.header-morado {{ background: #4F062A; color: white; text-align: center; font-weight: bold; }}';
        html += '.row-gris1 {{ background: #D0CEC1; }}';
        html += '.row-gris2 {{ background: #E3E2DA; }}';
        html += '.col-label {{ width: 45%; }}';
        html += '.col-value {{ width: 55%; text-align: center; }}';
        html += '.ranking-box {{ background: #ED1782; color: white; text-align: center; padding: 15px; font-size: 16pt; font-weight: bold; margin-bottom: 15px; }}';
        html += '</style></head><body>';
        
        // Título
        html += '<h1>Informe Técnico – Punto hidroeléctrico</h1>';
        
        // Ranking si existe
        if (ranking !== null) {{
            html += '<div class="ranking-box">⭐ RANKING #' + ranking + '</div>';
        }}
        
        // Fecha de generación
        html += '<table>';
        html += '<tr><td class="header-rosa col-label">Fecha de generación del informe</td>';
        html += '<td class="row-gris1 col-value">' + fechaGeneracion + '</td></tr>';
        html += '</table>';
        
        // INFORMACIÓN DEL PUNTO
        html += '<table>';
        html += '<tr><td colspan="2" class="header-morado">Información del punto</td></tr>';
        html += '<tr><td class="row-gris1 col-label">ID</td><td class="row-gris1 col-value">' + punto.id + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Municipio</td><td class="row-gris2 col-value">' + punto.municipio + '</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Departamento</td><td class="row-gris1 col-value">' + punto.departamento + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Región</td><td class="row-gris2 col-value">' + punto.region + '</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Coordenadas</td><td class="row-gris1 col-value">' + punto.lat.toFixed(6) + ', ' + punto.lon.toFixed(6) + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Capital más cercana</td><td class="row-gris2 col-value">' + punto.capital + ' (' + punto.depto_capital + ')</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Distancia a capital</td><td class="row-gris1 col-value">' + formatNumber(punto.dist_punto_capital) + ' m</td></tr>';
        html += '</table>';
        
        // ENERGÍA Y DEMANDA
        html += '<table>';
        html += '<tr><td colspan="2" class="header-morado">Energía y Demanda</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Caudal</td><td class="row-gris1 col-value">' + punto.caudal.toFixed(3) + ' m³/s (' + punto.caudal_cfs.toFixed(2) + ' cfs)</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Caída hidráulica</td><td class="row-gris2 col-value">' + punto.caida.toFixed(2) + ' m (' + punto.caida_ft.toFixed(2) + ' ft)</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Pendiente</td><td class="row-gris1 col-value">' + punto.pendiente.toFixed(4) + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Viviendas sin servicio</td><td class="row-gris2 col-value">' + Math.floor(punto.vss) + ' viviendas</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Zona climática</td><td class="row-gris1 col-value">' + punto.zona_clima + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Potencia pico</td><td class="row-gris2 col-value">' + punto.potencia_pico.toFixed(2) + ' kW/vivienda</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Turbinas disponibles</td><td class="row-gris1 col-value">' + (punto.turbinas ? punto.turbinas.length : 0) + ' tipo(s)</td></tr>';
        html += '</table>';
        
        // TURBINAS
        if (punto.turbinas && punto.turbinas.length > 0) {{
            punto.turbinas.forEach(function(turb, idx) {{
                html += '<table>';
                html += '<tr><td colspan="2" class="header-morado">Turbina ' + (idx + 1) + ': ' + turb.tipo.toUpperCase() + '</td></tr>';
                
                // Potencias
                html += '<tr><td class="row-gris1 col-label">Potencia máxima aprovechable</td><td class="row-gris1 col-value">' + turb.potencia_maxima.toFixed(2) + ' kW</td></tr>';
                html += '<tr><td class="row-gris2 col-label">Potencia para abastecer VSS</td><td class="row-gris2 col-value">' + turb.potencia_abastecer_vss.toFixed(2) + ' kW</td></tr>';
                html += '<tr><td class="row-gris1 col-label">Potencia usada para costes</td><td class="row-gris1 col-value">' + turb.potencia_usada_costes.toFixed(2) + ' kW</td></tr>';
                html += '<tr><td class="row-gris2 col-label">VSS abastecidas</td><td class="row-gris2 col-value">' + turb.vss_abastecibles + ' de ' + Math.floor(punto.vss) + '</td></tr>';
                
                // Cobertura
                var cobertura = turb.es_hibrida ? '⚠️ Híbrida recomendada' : '✓ Cobertura completa';
                html += '<tr><td class="row-gris1 col-label">Cobertura</td><td class="row-gris1 col-value">' + cobertura + '</td></tr>';
                html += '</table>';
                
                // Tabla CAPEX (3 columnas)
                html += '<table>';
                html += '<tr><td class="header-rosa">Partida</td><td class="header-rosa">USD</td><td class="header-rosa">COP</td></tr>';
                html += '<tr><td class="row-gris1">Turbina y generador</td><td class="row-gris1" style="text-align:right;">$' + formatNumber(turb.coste_turbina) + '</td><td class="row-gris1" style="text-align:right;">$' + formatNumber(turb.coste_turbina * tasaCambio) + '</td></tr>';
                html += '<tr><td class="row-gris2">Otros equipos</td><td class="row-gris2" style="text-align:right;">$' + formatNumber(turb.coste_equipos) + '</td><td class="row-gris2" style="text-align:right;">$' + formatNumber(turb.coste_equipos * tasaCambio) + '</td></tr>';
                html += '<tr><td class="row-gris1">Obra civil</td><td class="row-gris1" style="text-align:right;">$' + formatNumber(turb.coste_obra_civil) + '</td><td class="row-gris1" style="text-align:right;">$' + formatNumber(turb.coste_obra_civil * tasaCambio) + '</td></tr>';
                html += '<tr><td class="row-gris2">Instalación y puesta en marcha</td><td class="row-gris2" style="text-align:right;">$' + formatNumber(turb.coste_instalacion) + '</td><td class="row-gris2" style="text-align:right;">$' + formatNumber(turb.coste_instalacion * tasaCambio) + '</td></tr>';
                html += '<tr><td class="row-gris1">Línea de conexión eléctrica</td><td class="row-gris1" style="text-align:right;">$' + formatNumber(turb.coste_linea) + '</td><td class="row-gris1" style="text-align:right;">$' + formatNumber(turb.coste_linea * tasaCambio) + '</td></tr>';
                html += '<tr><td class="row-gris2">Costes ambientales</td><td class="row-gris2" style="text-align:right;">$' + formatNumber(turb.coste_ambiental) + '</td><td class="row-gris2" style="text-align:right;">$' + formatNumber(turb.coste_ambiental * tasaCambio) + '</td></tr>';
                html += '<tr><td class="row-gris1">Transporte</td><td class="row-gris1" style="text-align:right;">$' + formatNumber(turb.coste_transporte) + '</td><td class="row-gris1" style="text-align:right;">$' + formatNumber(turb.coste_transporte * tasaCambio) + '</td></tr>';
                html += '<tr><td class="row-gris2">Otros costes</td><td class="row-gris2" style="text-align:right;">$' + formatNumber(turb.otros_costes) + '</td><td class="row-gris2" style="text-align:right;">$' + formatNumber(turb.otros_costes * tasaCambio) + '</td></tr>';
                html += '<tr><td class="header-morado">CAPEX total</td><td class="header-morado" style="text-align:right;">$' + formatNumber(turb.capex_total) + '</td><td class="header-morado" style="text-align:right;">$' + formatNumber(turb.capex_total * tasaCambio) + '</td></tr>';
                html += '<tr><td class="row-gris1">OPEX Anual (3%)</td><td class="row-gris1" style="text-align:right;">$' + formatNumber(turb.opex) + '</td><td class="row-gris1" style="text-align:right;">$' + formatNumber(turb.opex * tasaCambio) + '</td></tr>';
                html += '<tr><td class="row-gris2">CAPEX Total / VSS</td><td class="row-gris2" style="text-align:right;">$' + formatNumber(turb.capex_por_vss) + '</td><td class="row-gris2" style="text-align:right;">$' + formatNumber(turb.capex_por_vss * tasaCambio) + '</td></tr>';
                html += '</table>';
            }});
        }}
        
        // TABLA DE ATRIBUTOS DEL PUNTO (al final)
        html += '<table>';
        html += '<tr><td colspan="2" class="header-morado">Atributos del punto</td></tr>';
        html += '<tr><td class="row-gris1 col-label">ID</td><td class="row-gris1 col-value">' + punto.id + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Latitud</td><td class="row-gris2 col-value">' + punto.lat.toFixed(6) + '</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Longitud</td><td class="row-gris1 col-value">' + punto.lon.toFixed(6) + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Caudal (m³/s)</td><td class="row-gris2 col-value">' + punto.caudal.toFixed(3) + '</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Caudal (cfs)</td><td class="row-gris1 col-value">' + punto.caudal_cfs.toFixed(2) + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Caída (m)</td><td class="row-gris2 col-value">' + punto.caida.toFixed(2) + '</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Caída (ft)</td><td class="row-gris1 col-value">' + punto.caida_ft.toFixed(2) + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Pendiente</td><td class="row-gris2 col-value">' + punto.pendiente.toFixed(4) + '</td></tr>';
        html += '<tr><td class="row-gris1 col-label">VSS</td><td class="row-gris1 col-value">' + Math.floor(punto.vss) + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Municipio</td><td class="row-gris2 col-value">' + punto.municipio + '</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Departamento</td><td class="row-gris1 col-value">' + punto.departamento + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Región</td><td class="row-gris2 col-value">' + punto.region + '</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Capital cercana</td><td class="row-gris1 col-value">' + punto.capital + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Depto. capital</td><td class="row-gris2 col-value">' + punto.depto_capital + '</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Distancia capital (m)</td><td class="row-gris1 col-value">' + formatNumber(punto.dist_punto_capital) + '</td></tr>';
        html += '<tr><td class="row-gris2 col-label">Zona climática</td><td class="row-gris2 col-value">' + punto.zona_clima + '</td></tr>';
        html += '<tr><td class="row-gris1 col-label">Potencia pico (kW/viv)</td><td class="row-gris1 col-value">' + punto.potencia_pico.toFixed(2) + '</td></tr>';
        if (ranking !== null) {{
            html += '<tr><td class="header-rosa">Ranking priorización</td><td class="header-rosa">#' + ranking + '</td></tr>';
        }}
        html += '</table>';
        
        html += '</body></html>';
        
        // Descargar como archivo .doc
        var blob = new Blob(['\\ufeff' + html], {{ type: 'application/msword' }});
        var link = document.createElement('a');
        var fecha = new Date();
        var nombreArchivo = 'Informe_Punto_' + punto.id + '_' + 
                          fecha.getFullYear() + 
                          String(fecha.getMonth()+1).padStart(2,'0') + 
                          String(fecha.getDate()).padStart(2,'0') + '.doc';
        
        link.href = URL.createObjectURL(blob);
        link.download = nombreArchivo;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    }}

    function priorizar() {{
        // Verificar que PAT o Cross Flow estén seleccionados
        var patSeleccionado = document.getElementById('turb-pat').checked;
        var crossFlowSeleccionado = document.getElementById('turb-crossflow').checked;
        
        if (!patSeleccionado && !crossFlowSeleccionado) {{
            alert('⚠️ ERROR: Priorización no disponible\\n\\nPara usar la priorización, debes tener seleccionada al menos una de estas turbinas:\\n\\n• PAT (Pump as Turbine)\\n• Cross Flow\\n\\nPor favor, marca una o ambas en el filtro de "Tipos de Turbina" e intenta de nuevo.');
            return;
        }}
        
        // Activar modo priorización
        modoPriorizacion = true;
        
        // Mostrar botón despriorizar, multiescenario y filtros de priorización
        document.getElementById('btn-despriorizar').style.display = 'block';
        document.getElementById('btn-multiescenario').style.display = 'block';
        document.getElementById('filtros-priorizacion').style.display = 'block';
        
        // Aplicar filtros y mostrar
        actualizar();
    }}
    
    function despriorizar() {{
        // Desactivar modo priorización
        modoPriorizacion = false;
        rankingPuntos = [];
        puntosPriorizadosCompletos = [];
        
        // Ocultar botón despriorizar, multiescenario y filtros de priorización
        document.getElementById('btn-despriorizar').style.display = 'none';
        document.getElementById('btn-multiescenario').style.display = 'none';
        document.getElementById('filtros-priorizacion').style.display = 'none';
        
        // Limpiar valores de filtros
        document.getElementById('ranking-top').value = '';
        document.getElementById('budget-max').value = '';
        document.getElementById('ranking-colores').checked = false;
        
        // Aplicar filtros normales
        actualizar();
    }}
    
    function aplicarFiltrosPriorizacion() {{
        if (modoPriorizacion) {{
            actualizar();
        }}
    }}
    
    // Variable global para la gráfica
    var graficaMultiescenario = null;
    
    function mostrarAnalisisMultiescenario() {{
        if (!modoPriorizacion || puntosPriorizadosCompletos.length === 0) {{
            alert('⚠️ No hay puntos priorizados para analizar.\\n\\nPrimero activa la priorización y asegúrate de que hay puntos visibles.');
            return;
        }}
        
        // Obtener la tasa de cambio actual
        var tasaCambio = parseFloat(document.getElementById('tasa-cambio').value) || 3711.71;
        
        // Ordenar puntos por ranking (de menor a mayor = mejor a peor)
        var puntosOrdenados = puntosPriorizadosCompletos.slice().sort(function(a, b) {{
            return a.ranking - b.ranking;
        }});
        
        // Calcular acumulados
        var datosGrafica = [];
        var vssAcumulado = 0;
        var capexAcumulado = 0;
        
        puntosOrdenados.forEach(function(item, index) {{
            var p = item.punto;
            var turbinaUsada = item.turbina;
            
            // Obtener VSS abastecibles del punto
            var vssAbastecibles = turbinaUsada ? turbinaUsada.vss_abastecibles : 0;
            
            // Obtener CAPEX de la turbina
            var capexPunto = turbinaUsada ? turbinaUsada.capex_total : 0;
            
            // Acumular
            vssAcumulado += vssAbastecibles;
            capexAcumulado += capexPunto;
            
            datosGrafica.push({{
                ranking: item.ranking,
                puntoId: p.id,
                municipio: p.municipio,
                vss: vssAbastecibles,
                capex: capexPunto,
                vssAcumulado: vssAcumulado,
                capexAcumulado: capexAcumulado,
                turbina: turbinaUsada ? turbinaUsada.tipo : 'N/A'
            }});
        }});
        
        // Actualizar estadísticas
        document.getElementById('stat-total-puntos').textContent = puntosOrdenados.length;
        document.getElementById('stat-total-vss').textContent = formatNumber(vssAcumulado);
        document.getElementById('stat-total-capex').textContent = '$' + formatNumber(capexAcumulado);
        var costoPromedio = vssAcumulado > 0 ? Math.round(capexAcumulado / vssAcumulado) : 0;
        document.getElementById('stat-costo-vss').textContent = '$' + formatNumber(costoPromedio);
        
        // Crear la gráfica
        var ctx = document.getElementById('grafica-multiescenario').getContext('2d');
        
        // Destruir gráfica anterior si existe
        if (graficaMultiescenario) {{
            graficaMultiescenario.destroy();
        }}
        
        // Preparar datos para Chart.js
        var labels = datosGrafica.map(function(d) {{ return '#' + d.ranking; }});
        var dataVSS = datosGrafica.map(function(d) {{ return d.vssAcumulado; }});
        var dataCAPEX = datosGrafica.map(function(d) {{ return d.capexAcumulado; }});
        
        // Crear datos para gráfica de dispersión (scatter)
        var scatterData = datosGrafica.map(function(d) {{
            return {{
                x: d.capexAcumulado,
                y: d.vssAcumulado,
                ranking: d.ranking,
                municipio: d.municipio,
                turbina: d.turbina,
                vssIndividual: d.vss,
                capexIndividual: d.capex
            }};
        }});
        
        graficaMultiescenario = new Chart(ctx, {{
            type: 'scatter',
            data: {{
                datasets: [{{
                    label: 'Acumulado VSS vs CAPEX',
                    data: scatterData,
                    backgroundColor: function(context) {{
                        var index = context.dataIndex;
                        var total = context.dataset.data.length;
                        // Gradiente de azul oscuro a azul claro según el ranking
                        var t = index / (total - 1 || 1);
                        var r = Math.round(13 + t * (173 - 13));
                        var g = Math.round(59 + t * (216 - 59));
                        var b = Math.round(102 + t * (230 - 102));
                        return 'rgba(' + r + ',' + g + ',' + b + ', 0.8)';
                    }},
                    borderColor: function(context) {{
                        var index = context.dataIndex;
                        var total = context.dataset.data.length;
                        var t = index / (total - 1 || 1);
                        var r = Math.round(13 + t * (173 - 13));
                        var g = Math.round(59 + t * (216 - 59));
                        var b = Math.round(102 + t * (230 - 102));
                        return 'rgb(' + r + ',' + g + ',' + b + ')';
                    }},
                    borderWidth: 1,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }},
                {{
                    label: 'Línea de tendencia',
                    data: scatterData,
                    type: 'line',
                    borderColor: 'rgba(52, 152, 219, 0.5)',
                    borderWidth: 2,
                    fill: false,
                    pointRadius: 0,
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Curva de Inversión Acumulada: VSS Abastecibles vs CAPEX Total',
                        font: {{ size: 16, weight: 'bold' }},
                        color: '#2C3E50'
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                var punto = context.raw;
                                return [
                                    'Ranking: #' + punto.ranking,
                                    'Municipio: ' + punto.municipio,
                                    'Turbina: ' + punto.turbina,
                                    'VSS: ' + punto.vssIndividual.toLocaleString(),
                                    'CAPEX: $' + punto.capexIndividual.toLocaleString()
                                ];
                            }}
                        }},
                        backgroundColor: 'rgba(44, 62, 80, 0.95)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        padding: 10,
                        displayColors: false
                    }},
                    legend: {{
                        display: true,
                        position: 'top',
                        labels: {{
                            usePointStyle: true,
                            padding: 15
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: 'CAPEX Acumulado (USD)',
                            font: {{ size: 14, weight: 'bold' }},
                            color: '#E74C3C'
                        }},
                        ticks: {{
                            callback: function(value) {{
                                return '$' + (value / 1000000).toFixed(1) + 'M';
                            }}
                        }},
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.1)'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: 'VSS Abastecibles Acumuladas',
                            font: {{ size: 14, weight: 'bold' }},
                            color: '#27AE60'
                        }},
                        ticks: {{
                            callback: function(value) {{
                                return value.toLocaleString();
                            }}
                        }},
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.1)'
                        }}
                    }}
                }}
            }}
        }});
        
        // Mostrar modal
        document.getElementById('modal-multiescenario').style.display = 'block';
    }}
    
    function cerrarModalMultiescenario() {{
        document.getElementById('modal-multiescenario').style.display = 'none';
    }}
    
    // Cerrar modal al hacer clic fuera
    window.onclick = function(event) {{
        var modal = document.getElementById('modal-multiescenario');
        if (event.target === modal) {{
            modal.style.display = 'none';
        }}
    }}
    
    function descargarDatos() {{
        var cmin = parseFloat(document.getElementById('caudal-min').value);
        var cmax = parseFloat(document.getElementById('caudal-max').value);
        var pmin = parseFloat(document.getElementById('pend-min').value);
        var vssMin = parseInt(document.getElementById('vss-min').value);
        
        // Obtener tipos de turbina seleccionados
        var turbinasSeleccionadas = [];
        if (document.getElementById('turb-francis').checked) turbinasSeleccionadas.push('Francis');
        if (document.getElementById('turb-pat').checked) turbinasSeleccionadas.push('PAT');
        if (document.getElementById('turb-pelton').checked) turbinasSeleccionadas.push('Pelton');
        if (document.getElementById('turb-kaplan').checked) turbinasSeleccionadas.push('Kaplan');
        if (document.getElementById('turb-lowhead').checked) turbinasSeleccionadas.push('Low Head');
        if (document.getElementById('turb-turgo').checked) turbinasSeleccionadas.push('Turgo');
        if (document.getElementById('turb-crossflow').checked) turbinasSeleccionadas.push('Cross Flow');
        
        // Obtener regiones seleccionadas
        var regionesSeleccionadas = [];
        if (document.getElementById('reg-pacifico').checked) regionesSeleccionadas.push('Región Pacífico');
        if (document.getElementById('reg-eje-cafetero').checked) regionesSeleccionadas.push('Región Eje Cafetero – Antioquia');
        if (document.getElementById('reg-centro-sur').checked) regionesSeleccionadas.push('Región Centro Sur');
        if (document.getElementById('reg-centro-oriente').checked) regionesSeleccionadas.push('Región Centro Oriente');
        if (document.getElementById('reg-caribe').checked) regionesSeleccionadas.push('Región Caribe');
        if (document.getElementById('reg-llano').checked) regionesSeleccionadas.push('Región Llano');
        if (document.getElementById('reg-sin-dato').checked) regionesSeleccionadas.push('');
        
        // Obtener CAPEX máximo y tasa de cambio
        var capexMaxInput = document.getElementById('capex-max').value;
        var capexMax = (capexMaxInput === '' || capexMaxInput === null) ? null : parseFloat(capexMaxInput);
        var tasaCambio = parseFloat(document.getElementById('tasa-cambio').value) || 3711.71;
        
        // Crear array de filas para construir el CSV
        var filas = [];
        
        // FILA 1: ENCABEZADOS (cada uno en una columna)
        var encabezados = [
            'ID_Punto',
            'Latitud',
            'Longitud',
            'Municipio',
            'Departamento',
            'Capital_Mas_Cercana',
            'Departamento_Capital',
            'Distancia_Punto_a_Capital_m',
            'Caudal_m3s',
            'Caida_Hidraulica_m',
            'Pendiente',
            'VSS_Viviendas_Sin_Servicio',
            'Zona_Climatica',
            'Potencia_Pico_kW',
            'Num_Turbinas_Aplicables',
            'Turbinas_Aplicables',
            'Turbina_Recomendada',
            'Potencia_Maxima_Aprovechable_kW',
            'Potencia_Abastecer_VSS_kW',
            'Potencia_Usada_Costes_kW',
            'Es_Opcion_Hibrida',
            'VSS_Abastecibles',
            'Coste_Turbina_USD',
            'Equipos_sin_Turbina_USD',
            'Obra_Civil_USD',
            'Instalacion_USD',
            'Linea_Electrica_USD',
            'Costes_Ambientales_USD',
            'Transporte_USD',
            'Otros_Costes_USD',
            'CAPEX_TOTAL_USD',
            'Coste_Turbina_COP',
            'Equipos_sin_Turbina_COP',
            'Obra_Civil_COP',
            'Instalacion_COP',
            'Linea_Electrica_COP',
            'Costes_Ambientales_COP',
            'Transporte_COP',
            'Otros_Costes_COP',
            'CAPEX_TOTAL_COP',
            'OPEX_Anual_USD',
            'OPEX_Anual_COP',
            'Costo_por_kW_USD',
            'Costo_por_kW_COP',
            'CAPEX_por_VSS_USD',
            'CAPEX_por_VSS_COP'
        ];
        
        // Si estamos en modo priorización, agregar Ranking como primera columna
        if (modoPriorizacion) {{
            encabezados.unshift('Ranking');
        }}
        
        filas.push(encabezados);
        
        var count = 0;
        var filasData = []; // Array temporal para almacenar filas con ranking
        
        // Filtrar y exportar puntos (CADA PUNTO = UNA FILA)
        puntos.forEach(function(p) {{
            var pasaCaudal = p.caudal > cmin && p.caudal < cmax;
            var pasaPendiente = p.pendiente > pmin;
            var pasaVss = p.vss >= vssMin;
            
            // Verificar si la región del punto está seleccionada
            var pasaRegion = regionesSeleccionadas.includes(p.region);
            
            // Verificar si el punto tiene al menos una turbina seleccionada
            var tieneTurbinaSeleccionada = false;
            if (p.turbinas && p.turbinas.length > 0) {{
                for (var i = 0; i < p.turbinas.length; i++) {{
                    if (turbinasSeleccionadas.includes(p.turbinas[i].tipo)) {{
                        tieneTurbinaSeleccionada = true;
                        break;
                    }}
                }}
            }}
            
            // Verificar CAPEX
            var pasaCapex = true;
            if (capexMax !== null && p.turbinas && p.turbinas.length > 0) {{
                pasaCapex = false;
                for (var i = 0; i < p.turbinas.length; i++) {{
                    if (p.turbinas[i].capex_total <= capexMax) {{
                        pasaCapex = true;
                        break;
                    }}
                }}
            }}
            
            // En modo priorización, verificar que el punto tenga ranking asignado
            if (modoPriorizacion && !rankingPuntos[p.id]) {{
                return; // Saltar este punto si no tiene ranking
            }}
            
            if (pasaCaudal && pasaPendiente && pasaVss && pasaRegion && tieneTurbinaSeleccionada && pasaCapex) {{
                
                // Crear FILA para este punto (cada dato en una columna)
                var fila = [];
                
                // Si estamos en modo priorización, agregar el ranking como primera columna
                var rankingActual = null;
                if (modoPriorizacion) {{
                    rankingActual = rankingPuntos[p.id] || 999999;
                    fila.push(rankingActual);
                }}
                
                // Columna: ID_Punto
                fila.push(p.id);
                
                // Columna: Latitud
                fila.push(p.lat.toFixed(6));
                
                // Columna: Longitud
                fila.push(p.lon.toFixed(6));
                
                // Columna: Municipio
                fila.push(p.municipio);
                
                // Columna: Departamento
                fila.push(p.departamento);
                
                // Columna: Capital_Mas_Cercana
                fila.push(p.capital);
                
                // Columna: Departamento_Capital
                fila.push(p.depto_capital);
                
                // Columna: Distancia_Punto_a_Capital_m
                fila.push(p.dist_punto_capital);
                
                // Columna: Caudal_m3s
                fila.push(p.caudal.toFixed(4));
                
                // Columna: Caida_Hidraulica_m
                fila.push(p.caida.toFixed(2));
                
                // Columna: Pendiente
                fila.push(p.pendiente.toFixed(4));
                
                // Columna: VSS_Viviendas_Sin_Servicio
                fila.push(p.vss);
                
                // Columna: Zona_Climatica
                fila.push(p.zona_clima);
                
                // Columna: Potencia_Pico_kW
                fila.push(p.potencia_pico.toFixed(2));
                
                // Determinar turbina recomendada (menor CAPEX)
                var mejorTurbina = null;
                var listaTurbinas = '';
                
                if (p.turbinas && p.turbinas.length > 0) {{
                    // Crear lista de todas las turbinas
                    listaTurbinas = p.turbinas.map(function(t) {{ return t.tipo; }}).join(' | ');
                    
                    // Encontrar la turbina con menor CAPEX
                    mejorTurbina = p.turbinas[0];
                    for (var i = 1; i < p.turbinas.length; i++) {{
                        if (p.turbinas[i].capex_total < mejorTurbina.capex_total) {{
                            mejorTurbina = p.turbinas[i];
                        }}
                    }}
                    
                    // Columna: Num_Turbinas_Aplicables
                    fila.push(p.turbinas.length);
                    
                    // Columna: Turbinas_Aplicables
                    fila.push(listaTurbinas);
                    
                    // Columna: Turbina_Recomendada
                    fila.push(mejorTurbina.tipo);
                    
                    // Columna: Potencia_Maxima_Aprovechable_kW
                    fila.push(mejorTurbina.potencia_maxima.toFixed(2));
                    
                    // Columna: Potencia_Abastecer_VSS_kW
                    fila.push(mejorTurbina.potencia_abastecer_vss.toFixed(2));
                    
                    // Columna: Potencia_Usada_Costes_kW
                    fila.push(mejorTurbina.potencia_usada_costes.toFixed(2));
                    
                    // Columna: Es_Opcion_Hibrida
                    fila.push(mejorTurbina.es_hibrida ? 'SÍ' : 'NO');
                    
                    // Columna: VSS_Abastecibles
                    fila.push(mejorTurbina.vss_abastecibles);
                    
                    // Columnas: CAPEX USD (8 partidas + total)
                    fila.push(mejorTurbina.coste_turbina.toFixed(2));
                    fila.push(mejorTurbina.coste_equipos.toFixed(2));
                    fila.push(mejorTurbina.coste_obra_civil.toFixed(2));
                    fila.push(mejorTurbina.coste_instalacion.toFixed(2));
                    fila.push(mejorTurbina.coste_linea.toFixed(2));
                    fila.push(mejorTurbina.coste_ambiental.toFixed(2));
                    fila.push(mejorTurbina.coste_transporte.toFixed(2));
                    fila.push(mejorTurbina.otros_costes.toFixed(2));
                    fila.push(mejorTurbina.capex_total.toFixed(2));
                    
                    // Columnas: CAPEX COP (8 partidas + total)
                    fila.push((mejorTurbina.coste_turbina * tasaCambio).toFixed(2));
                    fila.push((mejorTurbina.coste_equipos * tasaCambio).toFixed(2));
                    fila.push((mejorTurbina.coste_obra_civil * tasaCambio).toFixed(2));
                    fila.push((mejorTurbina.coste_instalacion * tasaCambio).toFixed(2));
                    fila.push((mejorTurbina.coste_linea * tasaCambio).toFixed(2));
                    fila.push((mejorTurbina.coste_ambiental * tasaCambio).toFixed(2));
                    fila.push((mejorTurbina.coste_transporte * tasaCambio).toFixed(2));
                    fila.push((mejorTurbina.otros_costes * tasaCambio).toFixed(2));
                    fila.push((mejorTurbina.capex_total * tasaCambio).toFixed(2));
                    
                    // Columnas: OPEX
                    fila.push(mejorTurbina.opex.toFixed(2));
                    fila.push((mejorTurbina.opex * tasaCambio).toFixed(2));
                    
                    // Columnas: Ratio por kW
                    var costoKw = mejorTurbina.capex_total / mejorTurbina.potencia_usada_costes;
                    fila.push(costoKw.toFixed(2));
                    fila.push((costoKw * tasaCambio).toFixed(2));
                    
                    // Columnas: CAPEX por VSS
                    fila.push(mejorTurbina.capex_por_vss.toFixed(2));
                    fila.push((mejorTurbina.capex_por_vss * tasaCambio).toFixed(2));
                    
                }} else {{
                    // Sin turbinas aplicables - rellenar columnas con valores por defecto
                    fila.push(0); // Num_Turbinas_Aplicables
                    fila.push('Sin turbinas aplicables'); // Turbinas_Aplicables
                    fila.push('N/A'); // Turbina_Recomendada
                    fila.push(0); // Potencia_Maxima_Aprovechable_kW
                    fila.push(0); // Potencia_Abastecer_VSS_kW
                    fila.push(0); // Potencia_Usada_Costes_kW
                    fila.push('N/A'); // Es_Opcion_Hibrida
                    fila.push(0); // VSS_Abastecibles
                    
                    // Rellenar todas las columnas de costes con 0
                    for (var i = 0; i < 24; i++) {{
                        fila.push(0);
                    }}
                }}
                
                // En modo priorización, guardar con ranking para ordenar después
                if (modoPriorizacion) {{
                    filasData.push({{ ranking: rankingActual, fila: fila }});
                }} else {{
                    filas.push(fila);
                }}
                count++;
            }}
        }});
        
        // Si estamos en modo priorización, ordenar por ranking (menor a mayor = mejor a peor)
        if (modoPriorizacion) {{
            filasData.sort(function(a, b) {{
                return a.ranking - b.ranking;
            }});
            // Agregar las filas ordenadas
            filasData.forEach(function(item) {{
                filas.push(item.fila);
            }});
        }}
        
        if (count === 0) {{
            alert('No hay puntos visibles para descargar. Ajusta los filtros.');
            return;
        }}
        
        // Convertir array de filas a CSV (cada elemento separado por PUNTO Y COMA para Excel español)
        var csv = filas.map(function(fila) {{
            return fila.map(function(valor) {{
                // Si el valor contiene punto y coma, encerrarlo entre comillas
                if (typeof valor === 'string' && (valor.includes(';') || valor.includes('|'))) {{
                    return '"' + valor + '"';
                }}
                return valor;
            }}).join(';');
        }}).join('\\n');
        
        // Añadir BOM UTF-8 para que Excel lo reconozca correctamente
        var BOM = '\\uFEFF';
        csv = BOM + csv;
        
        // Crear y descargar archivo CSV
        var blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
        var link = document.createElement('a');
        var url = URL.createObjectURL(blob);
        
        var fecha = new Date().toISOString().slice(0,10).replace(/-/g,'');
        var nombreArchivo = modoPriorizacion ? 
            'priorizacion_hidroelectrica_' + fecha + '_' + count + 'puntos.csv' :
            'puntos_hidroelectricos_' + fecha + '_' + count + 'puntos.csv';
        
        link.setAttribute('href', url);
        link.setAttribute('download', nombreArchivo);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        var mensaje = modoPriorizacion ?
            '✓ Descargados ' + count + ' puntos PRIORIZADOS\\n\\nOrdenados por Ranking (mejor a peor).\\nLa columna Ranking indica la posición.\\nTurbinas: solo PAT y Cross Flow.\\n\\nArchivo: ' + nombreArchivo :
            '✓ Descargados ' + count + ' puntos (cada punto = 1 fila)\\n\\nCada columna tiene un dato diferente.\\nLa turbina mostrada es la MÁS ECONÓMICA.\\nCostes calculados con potencia para abastecer VSS.\\nSe indica si requiere opción híbrida.\\n\\nArchivo: ' + nombreArchivo;
        
        alert(mensaje);
    }}
    
    function toggleTurbinas() {{
        var checkboxes = [
            document.getElementById('turb-francis'),
            document.getElementById('turb-pat'),
            document.getElementById('turb-pelton'),
            document.getElementById('turb-kaplan'),
            document.getElementById('turb-lowhead'),
            document.getElementById('turb-turgo'),
            document.getElementById('turb-crossflow')
        ];
        var allChecked = checkboxes.every(cb => cb.checked);
        checkboxes.forEach(cb => cb.checked = !allChecked);
    }}
    
    function toggleRegiones() {{
        var checkboxes = [
            document.getElementById('reg-pacifico'),
            document.getElementById('reg-eje-cafetero'),
            document.getElementById('reg-centro-sur'),
            document.getElementById('reg-centro-oriente'),
            document.getElementById('reg-caribe'),
            document.getElementById('reg-llano'),
            document.getElementById('reg-sin-dato')
        ];
        var allChecked = checkboxes.every(cb => cb.checked);
        checkboxes.forEach(cb => cb.checked = !allChecked);
    }}
    
    function actualizarValores() {{
        document.getElementById('cmin').textContent = parseFloat(document.getElementById('caudal-min').value).toFixed(2);
        document.getElementById('cmax').textContent = parseFloat(document.getElementById('caudal-max').value).toFixed(2);
        document.getElementById('pmin').textContent = parseFloat(document.getElementById('pend-min').value).toFixed(2);
        document.getElementById('vss-min-val').textContent = parseInt(document.getElementById('vss-min').value);
    }}
    
    function actualizar() {{
        var cmin = parseFloat(document.getElementById('caudal-min').value);
        var cmax = parseFloat(document.getElementById('caudal-max').value);
        var pmin = parseFloat(document.getElementById('pend-min').value);
        var vssMin = parseInt(document.getElementById('vss-min').value);
        
        // Obtener tipos de turbina seleccionados
        var turbinasSeleccionadas = [];
        if (document.getElementById('turb-francis').checked) turbinasSeleccionadas.push('Francis');
        if (document.getElementById('turb-pat').checked) turbinasSeleccionadas.push('PAT');
        if (document.getElementById('turb-pelton').checked) turbinasSeleccionadas.push('Pelton');
        if (document.getElementById('turb-kaplan').checked) turbinasSeleccionadas.push('Kaplan');
        if (document.getElementById('turb-lowhead').checked) turbinasSeleccionadas.push('Low Head');
        if (document.getElementById('turb-turgo').checked) turbinasSeleccionadas.push('Turgo');
        if (document.getElementById('turb-crossflow').checked) turbinasSeleccionadas.push('Cross Flow');
        
        // Obtener regiones seleccionadas
        var regionesSeleccionadas = [];
        if (document.getElementById('reg-pacifico').checked) regionesSeleccionadas.push('Región Pacífico');
        if (document.getElementById('reg-eje-cafetero').checked) regionesSeleccionadas.push('Región Eje Cafetero – Antioquia');
        if (document.getElementById('reg-centro-sur').checked) regionesSeleccionadas.push('Región Centro Sur');
        if (document.getElementById('reg-centro-oriente').checked) regionesSeleccionadas.push('Región Centro Oriente');
        if (document.getElementById('reg-caribe').checked) regionesSeleccionadas.push('Región Caribe');
        if (document.getElementById('reg-llano').checked) regionesSeleccionadas.push('Región Llano');
        if (document.getElementById('reg-sin-dato').checked) regionesSeleccionadas.push('');
        
        // Obtener CAPEX máximo (si está vacío, no aplicar filtro)
        var capexMaxInput = document.getElementById('capex-max').value;
        var capexMax = (capexMaxInput === '' || capexMaxInput === null) ? null : parseFloat(capexMaxInput);
        
        // Obtener tasa de cambio
        var tasaCambio = parseFloat(document.getElementById('tasa-cambio').value) || 3711.71;
        
        actualizarValores();
        
        // Definir función auxiliar ANTES de usarla
        function mostrarPuntoEnMapa(p, tasaCambio, ranking, soloPatCrossFlow, totalPuntos) {{
            var popupHTML = '<div style="max-height: 500px; overflow-y: auto; padding: 5px;">';
            
            // Si hay ranking, mostrarlo prominentemente
            if (ranking !== null) {{
                popupHTML += '<div style="background: linear-gradient(135deg, #E54D9A 0%, #FF0066 100%); color: white; padding: 12px; border-radius: 8px; margin-bottom: 10px; text-align: center; box-shadow: 0 4px 8px rgba(255,0,102,0.3);">';
                popupHTML += '<div style="font-size: 24px; font-weight: bold;">⭐ Ranking #' + ranking + '</div>';
                popupHTML += '</div>';
            }}
            
            // Botón Descargar Informe
            popupHTML += '<button onclick="descargarInforme(' + p.id + ', ' + tasaCambio + ', ' + (ranking !== null ? ranking : 'null') + ')" style="width: 100%; padding: 12px; background: linear-gradient(135deg, #5D0E41 0%, #E54D9A 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; margin-bottom: 10px; box-shadow: 0 3px 6px rgba(229,77,154,0.4);">';
            popupHTML += '📄 Descargar Informe Word';
            popupHTML += '</button>';
            
            // Información básica del punto
            popupHTML += '<div style="background: #F5E8F0; padding: 8px; border-radius: 4px; margin-bottom: 10px; border-left: 4px solid #E54D9A;">';
            popupHTML += '<div style="font-weight: bold; color: #5D0E41; margin-bottom: 6px;">📍 Información del Punto</div>';
            popupHTML += '<table style="font-size: 10px; width: 100%;">';
            popupHTML += '<tr><td style="padding: 2px;"><b>ID:</b></td><td style="padding: 2px;">' + p.id + '</td></tr>';
            popupHTML += '<tr><td style="padding: 2px;"><b>Municipio:</b></td><td style="padding: 2px;">' + p.municipio + '</td></tr>';
            popupHTML += '<tr><td style="padding: 2px;"><b>Departamento:</b></td><td style="padding: 2px;">' + p.departamento + '</td></tr>';
            popupHTML += '<tr><td style="padding: 2px;"><b>Región:</b></td><td style="padding: 2px;">' + p.region + '</td></tr>';
            popupHTML += '<tr><td style="padding: 2px;"><b>Coordenadas:</b></td><td style="padding: 2px;">' + p.lat.toFixed(4) + ', ' + p.lon.toFixed(4) + '</td></tr>';
            popupHTML += '</table>';
            popupHTML += '</div>';
            
            // Información de Energía y Demanda
            if (p.turbinas && p.turbinas.length > 0) {{
                popupHTML += '<div style="background: #FFF0F5; padding: 8px; border-radius: 4px; margin-bottom: 10px; border-left: 4px solid #FF0066;">';
                popupHTML += '<div style="font-weight: bold; color: #CC0052; margin-bottom: 6px;">⚡ Información de Energía y Demanda</div>';
                popupHTML += '<table style="font-size: 10px; width: 100%;">';
                popupHTML += '<tr><td style="padding: 2px;"><b>Caudal:</b></td><td style="padding: 2px;">' + p.caudal.toFixed(3) + ' m³/s (' + p.caudal_cfs.toFixed(2) + ' cfs)</td></tr>';
                popupHTML += '<tr><td style="padding: 2px;"><b>Caída hidráulica:</b></td><td style="padding: 2px;">' + p.caida.toFixed(2) + ' m (' + p.caida_ft.toFixed(2) + ' ft)</td></tr>';
                popupHTML += '<tr style="background: #FFF0F5;"><td style="padding: 2px;"><b>🏠 Viviendas Sin Servicio:</b></td><td style="padding: 2px;"><b>' + Math.floor(p.vss) + '</b> viviendas</td></tr>';
                popupHTML += '<tr><td style="padding: 2px;"><b>🌡️ Zona climática:</b></td><td style="padding: 2px;">' + p.zona_clima + '</td></tr>';
                popupHTML += '<tr><td style="padding: 2px;"><b>⚡ Potencia pico:</b></td><td style="padding: 2px;">' + p.potencia_pico.toFixed(2) + ' kW/vivienda</td></tr>';
                
                // Filtrar turbinas según modo
                var turbinasAMostrar = p.turbinas;
                if (soloPatCrossFlow) {{
                    turbinasAMostrar = p.turbinas.filter(function(t) {{
                        return t.tipo === 'PAT' || t.tipo === 'Cross Flow';
                    }});
                }}
                
                popupHTML += '<tr><td style="padding: 2px;"><b>Turbinas ' + (soloPatCrossFlow ? '(PAT/Cross Flow)' : 'disponibles') + ':</b></td><td style="padding: 2px;"><b>' + turbinasAMostrar.length + '</b> tipo' + (turbinasAMostrar.length !== 1 ? 's' : '') + '</td></tr>';
                popupHTML += '</table>';
                popupHTML += '</div>';
                
                // BOTÓN COMPARAR TURBINAS (solo si hay más de una en las filtradas)
                if (turbinasAMostrar.length > 1) {{
                    popupHTML += '<button onclick="toggleComparativa_' + p.id + '()" style="width: 100%; padding: 10px; margin-bottom: 10px; background: linear-gradient(135deg, #5D0E41 0%, #E54D9A 100%); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; box-shadow: 0 3px 6px rgba(229,77,154,0.4);">';
                    popupHTML += '🔍 Comparar ' + turbinasAMostrar.length + ' turbinas disponibles';
                    popupHTML += '</button>';
                    
                    // TABLA COMPARATIVA (usar turbinasAMostrar)
                    popupHTML += '<div id="comparativa_' + p.id + '" style="display: none; margin-bottom: 15px; background: #F5F3F0; padding: 12px; border-radius: 8px; border: 2px solid #667eea;">';
                    popupHTML += '<h4 style="margin: 0 0 10px 0; color: #667eea; font-size: 14px; text-align: center;">📊 Comparativa de Turbinas</h4>';
                    
                    popupHTML += '<div style="overflow-x: auto;">';
                    popupHTML += '<table style="font-size: 9px; width: 100%; border-collapse: collapse; background: white;">';
                    
                    // ENCABEZADO
                    popupHTML += '<tr style="background: #5D0E41; color: white; font-weight: bold;">';
                    popupHTML += '<th style="padding: 6px; border: 1px solid #D0CCC8; text-align: left; position: sticky; left: 0; background: #5D0E41; z-index: 2;">Métrica</th>';
                    turbinasAMostrar.forEach(function(turb) {{
                        popupHTML += '<th style="padding: 6px; border: 1px solid #D0CCC8; text-align: center; min-width: 80px;">' + turb.tipo + '</th>';
                    }});
                    popupHTML += '</tr>';
                    
                    // FILA: Potencia máxima aprovechable
                    popupHTML += '<tr style="background: #FFF0F5;">';
                    popupHTML += '<td style="padding: 4px; border: 1px solid #D0CCC8; font-weight: bold; position: sticky; left: 0; background: #FFF0F5; z-index: 1;">Potencia Máx. Aprov. (kW)</td>';
                    var maxPotenciaMax = Math.max.apply(Math, turbinasAMostrar.map(function(t) {{ return t.potencia_maxima; }}));
                    turbinasAMostrar.forEach(function(turb) {{
                        var esMax = turb.potencia_maxima === maxPotenciaMax;
                        popupHTML += '<td style="padding: 4px; border: 1px solid #D0CCC8; text-align: center;' + (esMax ? ' background: #FCE4EC; font-weight: bold;' : '') + '">' + turb.potencia_maxima.toFixed(2) + (esMax ? ' ⭐' : '') + '</td>';
                    }});
                    popupHTML += '</tr>';
                    
                    // FILA: Potencia a abastecer VSS
                    popupHTML += '<tr>';
                    popupHTML += '<td style="padding: 4px; border: 1px solid #D0CCC8; font-weight: bold; position: sticky; left: 0; background: white; z-index: 1;">Potencia Abastecer VSS (kW)</td>';
                    turbinasAMostrar.forEach(function(turb) {{
                        popupHTML += '<td style="padding: 4px; border: 1px solid #D0CCC8; text-align: center;">' + turb.potencia_abastecer_vss.toFixed(2) + '</td>';
                    }});
                    popupHTML += '</tr>';
                    
                    // FILA: Estado
                    popupHTML += '<tr>';
                    popupHTML += '<td style="padding: 4px; border: 1px solid #D0CCC8; font-weight: bold; position: sticky; left: 0; background: white; z-index: 1;">Estado</td>';
                    turbinasAMostrar.forEach(function(turb) {{
                        var estado = turb.es_hibrida ? 'Híbrida ⚠️' : 'Completa ✓';
                        var bgColor = turb.es_hibrida ? '#FFF0F5' : '#FCE4EC';
                        popupHTML += '<td style="padding: 4px; border: 1px solid #D0CCC8; text-align: center; background: ' + bgColor + '; font-size: 9px; font-weight: bold;">' + estado + '</td>';
                    }});
                    popupHTML += '</tr>';
                    
                    // FILA: CAPEX Total USD
                    popupHTML += '<tr>';
                    popupHTML += '<td style="padding: 4px; border: 1px solid #D0CCC8; font-weight: bold; position: sticky; left: 0; background: white; z-index: 1;">CAPEX Total (USD)</td>';
                    var minCapex = Math.min.apply(Math, turbinasAMostrar.map(function(t) {{ return t.capex_total; }}));
                    turbinasAMostrar.forEach(function(turb) {{
                        var esMin = turb.capex_total === minCapex;
                        popupHTML += '<td style="padding: 4px; border: 1px solid #D0CCC8; text-align: center;' + (esMin ? ' background: #FCE4EC; font-weight: bold;' : '') + '">$' + formatNumber(turb.capex_total) + (esMin ? ' ⭐' : '') + '</td>';
                    }});
                    popupHTML += '</tr>';
                    
                    // FILA: CAPEX por VSS
                    popupHTML += '<tr style="background: #F5F3F0;">';
                    popupHTML += '<td style="padding: 4px; border: 1px solid #D0CCC8; font-weight: bold; position: sticky; left: 0; background: #F5F3F0; z-index: 1;">USD/VSS</td>';
                    var minCapexVss = Math.min.apply(Math, turbinasAMostrar.map(function(t) {{ return t.capex_por_vss; }}));
                    turbinasAMostrar.forEach(function(turb) {{
                        var esMin = Math.abs(turb.capex_por_vss - minCapexVss) < 0.01;
                        popupHTML += '<td style="padding: 4px; border: 1px solid #D0CCC8; text-align: center;' + (esMin ? ' background: #FCE4EC; font-weight: bold;' : '') + '">$' + formatNumber(turb.capex_por_vss) + (esMin ? ' ⭐' : '') + '</td>';
                    }});
                    popupHTML += '</tr>';
                    
                    popupHTML += '</table>';
                    popupHTML += '</div>';
                    
                    // Análisis automático
                    popupHTML += '<div style="margin-top: 10px; padding: 8px; background: #FFF0F5; border-radius: 4px; font-size: 10px;">';
                    popupHTML += '<b>💡 Análisis:</b><br>';
                    var mejorCapex = turbinasAMostrar.reduce(function(prev, curr) {{ return prev.capex_total < curr.capex_total ? prev : curr; }});
                    var mejorCapexVss = turbinasAMostrar.reduce(function(prev, curr) {{ return prev.capex_por_vss < curr.capex_por_vss ? prev : curr; }});
                    popupHTML += '• <b>Más económica:</b> ' + mejorCapex.tipo + ' ($' + formatNumber(mejorCapex.capex_total) + ')<br>';
                    popupHTML += '• <b>Menor costo por vivienda:</b> ' + mejorCapexVss.tipo + ' ($' + formatNumber(mejorCapexVss.capex_por_vss) + '/VSS)';
                    popupHTML += '</div>';
                    
                    popupHTML += '</div>';
                }}
                
                // Para cada turbina aplicable (filtrada)
                turbinasAMostrar.forEach(function(turb, idx) {{
                    var bgColor = idx % 2 === 0 ? '#F5F3F0' : '#ffffff';
                    
                    popupHTML += '<div style="background: ' + bgColor + '; padding: 10px; border-radius: 6px; margin-bottom: 12px; border: 2px solid #D0CCC8;">';
                    popupHTML += '<div style="background: linear-gradient(135deg, #5D0E41 0%, #E54D9A 100%); color: white; padding: 8px; border-radius: 4px; margin-bottom: 8px; text-align: center;">';
                    popupHTML += '<span style="font-size: 14px; font-weight: bold;">🔧 ' + turb.tipo + '</span>';
                    popupHTML += '</div>';
                    
                    // Información de potencias
                    popupHTML += '<div style="background: #FFF0F5; padding: 8px; border-radius: 4px; margin-bottom: 8px;">';
                    popupHTML += '<div style="font-size: 10px;">';
                    popupHTML += '<b>⚡ Potencia máxima aprovechable:</b> ' + turb.potencia_maxima.toFixed(2) + ' kW<br>';
                    popupHTML += '<b>🏠 Potencia a abastecer ' + Math.floor(p.vss) + ' VSS:</b> ' + turb.potencia_abastecer_vss.toFixed(2) + ' kW<br>';
                    popupHTML += '<b>💡 Potencia usada para costes:</b> ' + turb.potencia_usada_costes.toFixed(2) + ' kW';
                    
                    if (turb.es_hibrida) {{
                        popupHTML += '<div style="background: #FFF0F5; border: 2px solid #FF0066; padding: 6px; border-radius: 4px; margin-top: 6px;">';
                        popupHTML += '<b style="color: #CC0052;">⚠️ OPCIÓN HÍBRIDA RECOMENDADA</b><br>';
                        popupHTML += '<span style="font-size: 9px;">La potencia máxima (' + turb.potencia_maxima.toFixed(2) + ' kW) no cubre la demanda total (' + turb.potencia_abastecer_vss.toFixed(2) + ' kW).</span><br>';
                        popupHTML += '<span style="font-size: 9px;"><b>VSS abastecibles solo con hidro:</b> ' + turb.vss_abastecibles + ' de ' + Math.floor(p.vss) + ' viviendas</span><br>';
                        popupHTML += '<span style="font-size: 9px; font-style: italic;">Se recomienda complementar con otra fuente de energía.</span>';
                        popupHTML += '</div>';
                    }} else {{
                        popupHTML += '<div style="background: #FCE4EC; border: 2px solid #E54D9A; padding: 4px; border-radius: 4px; margin-top: 6px; font-size: 9px;">';
                        popupHTML += '<b style="color: #5D0E41;">✓ La potencia hidráulica cubre todas las ' + Math.floor(p.vss) + ' viviendas</b>';
                        popupHTML += '</div>';
                    }}
                    
                    popupHTML += '</div>';
                    popupHTML += '</div>';
                    
                    // Tabla CAPEX
                    popupHTML += '<div>';
                    popupHTML += '<div style="background: #E54D9A; color: white; padding: 4px 8px; border-radius: 3px; font-size: 11px; font-weight: bold; margin-bottom: 4px;">💰 CAPEX (Costes de Inversión)</div>';
                    popupHTML += '<table style="font-size: 10px; width: 100%; border-collapse: collapse;">';
                    popupHTML += '<tr style="background: #F5E8F0; font-weight: bold;"><td style="padding: 4px; border: 1px solid #D0CCC8;">Partida</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">USD</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">COP</td></tr>';
                    
                    popupHTML += '<tr><td style="padding: 4px; border: 1px solid #D0CCC8;">Turbina y generador</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_turbina) + '</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_turbina * tasaCambio) + '</td></tr>';
                    popupHTML += '<tr><td style="padding: 4px; border: 1px solid #D0CCC8;">Otros equipos</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_equipos) + '</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_equipos * tasaCambio) + '</td></tr>';
                    popupHTML += '<tr><td style="padding: 4px; border: 1px solid #D0CCC8;">Obra civil</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_obra_civil) + '</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_obra_civil * tasaCambio) + '</td></tr>';
                    popupHTML += '<tr><td style="padding: 4px; border: 1px solid #D0CCC8;">Instalación y puesta en marcha</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_instalacion) + '</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_instalacion * tasaCambio) + '</td></tr>';
                    popupHTML += '<tr><td style="padding: 4px; border: 1px solid #D0CCC8;">Línea de conexión eléctrica</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_linea) + '</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_linea * tasaCambio) + '</td></tr>';
                    popupHTML += '<tr><td style="padding: 4px; border: 1px solid #D0CCC8;">Costes ambientales</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_ambiental) + '</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_ambiental * tasaCambio) + '</td></tr>';
                    popupHTML += '<tr><td style="padding: 4px; border: 1px solid #D0CCC8;">Transporte</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_transporte) + '</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.coste_transporte * tasaCambio) + '</td></tr>';
                    popupHTML += '<tr><td style="padding: 4px; border: 1px solid #D0CCC8;">Otros costes</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.otros_costes) + '</td><td style="padding: 4px; text-align: right; border: 1px solid #D0CCC8;">$' + formatNumber(turb.otros_costes * tasaCambio) + '</td></tr>';
                    
                    popupHTML += '<tr style="background: #E54D9A; color: white; font-weight: bold;"><td style="padding: 4px; border: 1px solid #E54D9A;">CAPEX TOTAL</td><td style="padding: 4px; text-align: right; border: 1px solid #E54D9A;">$' + formatNumber(turb.capex_total) + '</td><td style="padding: 4px; text-align: right; border: 1px solid #E54D9A;">$' + formatNumber(turb.capex_total * tasaCambio) + '</td></tr>';
                    popupHTML += '</table>';
                    popupHTML += '</div>';
                    
                    // Tabla OPEX
                    popupHTML += '<div style="margin-top: 8px;">';
                    popupHTML += '<div style="background: #8B8B6E; color: white; padding: 4px 8px; border-radius: 3px; font-size: 11px; font-weight: bold; margin-bottom: 4px;">🔧 OPEX (Costes de Operación Anual)</div>';
                    popupHTML += '<table style="font-size: 10px; width: 100%; border-collapse: collapse;">';
                    popupHTML += '<tr style="background: #8B8B6E; color: white; font-weight: bold;"><td style="padding: 4px; border: 1px solid #8B8B6E;">OPEX Anual (3% del CAPEX)</td><td style="padding: 4px; text-align: right; border: 1px solid #8B8B6E;">$' + formatNumber(turb.opex) + ' USD</td><td style="padding: 4px; text-align: right; border: 1px solid #8B8B6E;">$' + formatNumber(turb.opex * tasaCambio) + ' COP</td></tr>';
                    popupHTML += '</table>';
                    popupHTML += '</div>';
                    
                    // CAPEX por VSS
                    popupHTML += '<div style="margin-top: 8px;">';
                    popupHTML += '<div style="background: #5D5D4D; color: white; padding: 4px 8px; border-radius: 3px; font-size: 11px; font-weight: bold; margin-bottom: 4px;">💰 Costo por Vivienda</div>';
                    popupHTML += '<table style="font-size: 10px; width: 100%; border-collapse: collapse;">';
                    popupHTML += '<tr style="background: #5D5D4D; color: white; font-weight: bold;"><td style="padding: 4px; border: 1px solid #5D5D4D;">CAPEX Total / VSS</td><td style="padding: 4px; text-align: right; border: 1px solid #5D5D4D;">$' + formatNumber(turb.capex_por_vss) + ' USD/VSS</td><td style="padding: 4px; text-align: right; border: 1px solid #5D5D4D;">$' + formatNumber(turb.capex_por_vss * tasaCambio) + ' COP/VSS</td></tr>';
                    popupHTML += '</table>';
                    popupHTML += '</div>';
                    
                    popupHTML += '</div>';
                }});
            }}
            
            // Atributos desplegables
            popupHTML += '<button onclick="toggleAtributos_' + p.id + '()" style="width: 100%; padding: 8px; margin-top: 10px; margin-bottom: 5px; background: #5D5D4D; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 11px;">';
            popupHTML += '📋 Ver todos los atributos';
            popupHTML += '</button>';
            
            popupHTML += '<div id="atributos_' + p.id + '" style="display: none; margin-top: 5px;">';
            popupHTML += '<div style="background: #F5F3F0; padding: 8px; border-radius: 4px; border: 1px solid #D0CCC8;">';
            popupHTML += '<div style="font-weight: bold; color: #555; margin-bottom: 4px; font-size: 11px;">Todos los atributos:</div>';
            popupHTML += '<table style="font-size: 11px; width: 100%;">';
            
            for (var attr in p.todos_atributos) {{
                popupHTML += '<tr><td style="font-weight: bold; padding: 2px;">' + attr + ':</td>';
                popupHTML += '<td style="padding: 2px;">' + p.todos_atributos[attr] + '</td></tr>';
            }}
            
            popupHTML += '</table>';
            popupHTML += '</div>';
            popupHTML += '</div>';
            
            popupHTML += '</div>';
            
            var colorMarcador = '#00FF00'; // Color por defecto (verde)
            
            if (soloPatCrossFlow) {{
                // Estamos en modo priorización
                var usarColoresRanking = document.getElementById('ranking-colores') && document.getElementById('ranking-colores').checked;
                
                if (usarColoresRanking && ranking !== null && totalPuntos > 0) {{
                    // Usar color según ranking (amarillo mejor, magenta peor)
                    colorMarcador = getColorPorRanking(ranking, totalPuntos);
                }} else {{
                    // Color fijo para priorización sin colores
                    colorMarcador = '#f5576c';
                }}
            }}
            
            L.circleMarker([p.lat, p.lon], {{
                radius: 2,
                fillColor: colorMarcador,
                color: colorMarcador,
                weight: soloPatCrossFlow ? 3 : 2,
                opacity: 0.8,
                fillOpacity: 0.8
            }}).bindPopup(popupHTML, {{maxWidth: 450}}).addTo(layer);
        }}
        
        if (layer) layer.remove();
        layer = L.layerGroup();
        var count = 0;
        
        // Si estamos en modo priorización, calcular ranking
        if (modoPriorizacion) {{
            // Filtrar puntos que tengan PAT o Cross Flow y cumplan otros filtros
            var puntosPriorizables = [];
            
            puntos.forEach(function(p) {{
                var pasaCaudal = p.caudal > cmin && p.caudal < cmax;
                var pasaPendiente = p.pendiente > pmin;
                var pasaVss = p.vss >= vssMin;
                var pasaRegion = regionesSeleccionadas.includes(p.region);
                
                // Verificar si tiene PAT o Cross Flow
                var tienePAToCrossFlow = false;
                var mejorCapexPorVss = Infinity;
                var mejorTurbinaPriorizada = null;
                
                if (p.turbinas && p.turbinas.length > 0) {{
                    for (var i = 0; i < p.turbinas.length; i++) {{
                        var turb = p.turbinas[i];
                        if (turb.tipo === 'PAT' || turb.tipo === 'Cross Flow') {{
                            tienePAToCrossFlow = true;
                            if (turb.capex_por_vss < mejorCapexPorVss) {{
                                mejorCapexPorVss = turb.capex_por_vss;
                                mejorTurbinaPriorizada = turb;
                            }}
                        }}
                    }}
                }}
                
                // Verificar CAPEX si hay filtro
                var pasaCapex = true;
                if (capexMax !== null && mejorCapexPorVss !== Infinity) {{
                    // Buscar si alguna turbina PAT o Cross Flow cumple con CAPEX
                    pasaCapex = false;
                    for (var i = 0; i < p.turbinas.length; i++) {{
                        var turb = p.turbinas[i];
                        if ((turb.tipo === 'PAT' || turb.tipo === 'Cross Flow') && turb.capex_total <= capexMax) {{
                            pasaCapex = true;
                            break;
                        }}
                    }}
                }}
                
                if (pasaCaudal && pasaPendiente && pasaVss && pasaRegion && tienePAToCrossFlow && pasaCapex) {{
                    puntosPriorizables.push({{
                        punto: p,
                        capex_por_vss: mejorCapexPorVss,
                        turbina: mejorTurbinaPriorizada
                    }});
                }}
            }});
            
            // Ordenar por CAPEX por VSS (menor a mayor)
            puntosPriorizables.sort(function(a, b) {{
                return a.capex_por_vss - b.capex_por_vss;
            }});
            
            // Guardar todos los puntos priorizados CON SU RANKING antes de filtrar
            puntosPriorizadosCompletos = puntosPriorizables.map(function(item, index) {{
                return {{
                    punto: item.punto,
                    capex_por_vss: item.capex_por_vss,
                    turbina: item.turbina,
                    ranking: index + 1
                }};
            }});
            
            // APLICAR FILTROS DE PRIORIZACIÓN
            var topN = parseInt(document.getElementById('ranking-top').value);
            var budgetMax = parseFloat(document.getElementById('budget-max').value);
            
            // Filtro Top N
            if (!isNaN(topN) && topN > 0) {{
                puntosPriorizables = puntosPriorizables.slice(0, topN);
            }}
            
            // Filtro Budget (sumar CAPEX desde ranking #1)
            if (!isNaN(budgetMax) && budgetMax > 0) {{
                var sumaCapex = 0;
                var puntosDentroBudget = [];
                
                for (var i = 0; i < puntosPriorizables.length; i++) {{
                    var capexPunto = puntosPriorizables[i].punto.turbinas.reduce(function(min, turb) {{
                        if (turb.tipo === 'PAT' || turb.tipo === 'Cross Flow') {{
                            return Math.min(min, turb.capex_total);
                        }}
                        return min;
                    }}, Infinity);
                    
                    if (sumaCapex + capexPunto <= budgetMax) {{
                        puntosDentroBudget.push(puntosPriorizables[i]);
                        sumaCapex += capexPunto;
                    }} else {{
                        break;
                    }}
                }}
                
                puntosPriorizables = puntosDentroBudget;
            }}
            
            // Asignar ranking
            rankingPuntos = [];
            puntosPriorizables.forEach(function(item, index) {{
                rankingPuntos[item.punto.id] = index + 1;
            }});
            
            // Guardar total de puntos para colores
            var totalPuntosRanking = puntosPriorizables.length;
            
            // Mostrar puntos priorizados
            puntosPriorizables.forEach(function(item) {{
                var p = item.punto;
                var ranking = rankingPuntos[p.id];
                
                mostrarPuntoEnMapa(p, tasaCambio, ranking, true, totalPuntosRanking);
                count++;
            }});
        }} else {{
            // Modo normal (sin priorización)
            puntos.forEach(function(p) {{
            var pasaCaudal = p.caudal > cmin && p.caudal < cmax;
            var pasaPendiente = p.pendiente > pmin;
            var pasaVss = p.vss >= vssMin;
            
            // Verificar si la región del punto está seleccionada
            var pasaRegion = regionesSeleccionadas.includes(p.region);
            
            // Verificar si el punto tiene al menos una turbina seleccionada
            var tieneTurbinaSeleccionada = false;
            if (p.turbinas && p.turbinas.length > 0) {{
                for (var i = 0; i < p.turbinas.length; i++) {{
                    if (turbinasSeleccionadas.includes(p.turbinas[i].tipo)) {{
                        tieneTurbinaSeleccionada = true;
                        break;
                    }}
                }}
            }}
            
            // Verificar si el punto tiene al menos una turbina con CAPEX <= capexMax
            var pasaCapex = true;  // Por defecto pasa si no hay filtro
            if (capexMax !== null && p.turbinas && p.turbinas.length > 0) {{
                pasaCapex = false;  // Cambiar a false, debe encontrar al menos una que cumpla
                for (var i = 0; i < p.turbinas.length; i++) {{
                    if (p.turbinas[i].capex_total <= capexMax) {{
                        pasaCapex = true;
                        break;
                    }}
                }}
            }}
            
            if (pasaCaudal && pasaPendiente && pasaVss && pasaRegion && tieneTurbinaSeleccionada && pasaCapex) {{
                mostrarPuntoEnMapa(p, tasaCambio, null, false, 0);
                count++;
            }}
        }});
        }}
        
        layer.addTo(map_{mapa._id});
        document.getElementById('count').textContent = formatNumber(count);
        
        layer.addTo(map_{mapa._id});
        document.getElementById('count').textContent = formatNumber(count);
        
        // Crear funciones toggleComparativa para cada punto con múltiples turbinas
        puntos.forEach(function(p) {{
            if (p.turbinas && p.turbinas.length > 1) {{
                window['toggleComparativa_' + p.id] = function() {{
                    var div = document.getElementById('comparativa_' + p.id);
                    if (div) {{
                        if (div.style.display === 'none') {{
                            div.style.display = 'block';
                        }} else {{
                            div.style.display = 'none';
                        }}
                    }}
                }};
            }}
            
            // Función para mostrar/ocultar atributos (para todos los puntos)
            window['toggleAtributos_' + p.id] = function() {{
                var div = document.getElementById('atributos_' + p.id);
                var btn = event.target;
                if (div) {{
                    if (div.style.display === 'none') {{
                        div.style.display = 'block';
                        btn.textContent = '📋 Ocultar atributos';
                    }} else {{
                        div.style.display = 'none';
                        btn.textContent = '📋 Ver todos los atributos';
                    }}
                }}
            }};
        }});
    }}
    
    function resetear() {{
        document.getElementById('caudal-min').value = {CAUDAL_MIN_INICIAL};
        document.getElementById('caudal-max').value = {CAUDAL_MAX_INICIAL};
        document.getElementById('pend-min').value = {PENDIENTE_MIN_INICIAL};
        document.getElementById('vss-min').value = {vss_min_inicial};
        
        // Limpiar filtro de CAPEX
        document.getElementById('capex-max').value = '';
        
        // Resetear tasa de cambio
        document.getElementById('tasa-cambio').value = '3711.71';
        
        // Marcar todas las turbinas
        document.getElementById('turb-francis').checked = true;
        document.getElementById('turb-pat').checked = true;
        document.getElementById('turb-pelton').checked = true;
        document.getElementById('turb-kaplan').checked = true;
        document.getElementById('turb-lowhead').checked = true;
        document.getElementById('turb-turgo').checked = true;
        document.getElementById('turb-crossflow').checked = true;
        
        // Marcar todas las regiones
        document.getElementById('reg-pacifico').checked = true;
        document.getElementById('reg-eje-cafetero').checked = true;
        document.getElementById('reg-centro-sur').checked = true;
        document.getElementById('reg-centro-oriente').checked = true;
        document.getElementById('reg-caribe').checked = true;
        document.getElementById('reg-llano').checked = true;
        document.getElementById('reg-sin-dato').checked = true;
        
        actualizarValores();
        actualizar();
    }}
    
    setTimeout(function() {{
        actualizarValores();
        actualizar();
    }}, 500);
    </script>
    '''
    
    mapa.get_root().html.add_child(folium.Element(controles_html))
    mapa.get_root().html.add_child(folium.Element(javascript))
    
    folium.LayerControl(collapsed=False).add_to(mapa)
    plugins.Fullscreen().add_to(mapa)
    plugins.MiniMap(toggle_display=True).add_to(mapa)
    
    print("✓ Mapa creado")
    return mapa

# ====================================================================
# PROGRAMA PRINCIPAL
# ====================================================================

if __name__ == "__main__":
    try:
        puntos = cargar_shapefile_puntos(RUTA_SHAPEFILE_PUNTOS)
        if puntos is None:
            exit(1)
        
        total_original = len(puntos)
        
        capas = {}
        capas_exitosas = 0
        capas_fallidas = 0
        
        if DESCARGAR_CAPAS:
            print("\n" + "="*70)
            print("DESCARGANDO CAPAS")
            print("="*70 + "\n")
            
            for key, cfg in CAPAS_CONFIG.items():
                gdf = descargar_capa_desde_api(cfg['id'], cfg['nombre'])
                if gdf is not None:
                    capas[key] = {'geodataframe': gdf, 'config': cfg}
                    capas_exitosas += 1
                else:
                    capas_fallidas += 1
            
            print(f"\n📊 Resumen de capas: {capas_exitosas} exitosas, {capas_fallidas} fallidas")
        else:
            print("\n⚠️  DESCARGA DE CAPAS DESHABILITADA")
            print("   Para habilitar, cambia DESCARGAR_CAPAS = True en la configuración\n")
        
        puntos_filtrados = filtrar_puntos_fuera_de_areas(puntos, capas)
        mapa = crear_mapa_interactivo(puntos_filtrados, capas, total_original)
        
        nombre = "mapa_final.html"
        mapa.save(nombre)
        
        print("\n" + "="*70)
        print("✅ VERSIÓN CON FILTROS SELECTIVOS")
        print("="*70)
        print(f"\n📂 {nombre}")
        print(f"\n🎨 ICONOS:")
        print(f"   • VSS: 🏠 (Viviendas Sin Servicio)")
        print(f"   • Distancia: 🏘️ (Distancia al municipio)")
        print(f"\n🚫 CAPAS RESTRICTIVAS (excluyen puntos):")
        print(f"   • Parques Arqueológicos")
        print(f"   • Parques Nacionales (PNN)")
        print(f"\n👁️  CAPAS SOLO VISUALES (NO excluyen puntos):")
        print(f"   • Tierras Comunidades Negras")
        print(f"   • Resguardos Indígenas")
        print(f"   • Complejos de Páramo")
        print(f"   • Áreas Protección Local")
        print(f"   • Áreas Protección Regional")
        print(f"   • Reservas Naturales (RNSC)")
        print(f"   • Áreas Protegidas (RUNAP)")
        print(f"   • Reservas Forestales")
        print(f"\n⚙️ FILTROS:")
        print(f"   • Caudal: {CAUDAL_MIN_INICIAL} - {CAUDAL_MAX_INICIAL}")
        print(f"   • Pendiente: > {PENDIENTE_MIN_INICIAL}")
        print(f"   • VSS: >= 0 (slider empieza en 0)")
        print(f"   • Distancia: <= máximo (slider empieza en máximo)")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
