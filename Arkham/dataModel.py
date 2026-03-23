"""
Data Model — guarda la información que obtenemos en dataConnector para que se
visualice correctamente en tablas dentro de la base de datos nuclear.db.
Cada función se encarga de leer un archivo .parquet distinto y persistirlo
en su tabla correspondiente, manteniendo la integridad referencial entre ellas.
"""

# Importamos las dependencias necesarias para manejo de archivos, base de datos y datos tabulares
import logging
import sqlite3
from pathlib import Path
import pandas as pd
import json
from datetime import datetime, timezone

"""
Configuración del logger para registrar el flujo de ejecución en consola
level=INFO significa que solo vemos mensajes informativos, advertencias y errores
format define cómo se ve cada línea: fecha, nivel y mensaje
datefmt especifica que la fecha se muestre como YYYY-MM-DD HH:MM:SS
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

"""
CARPETA_DATOS apunta a la carpeta /data donde viven todos los archivos .parquet descargados
RUTA_BD indica el archivo SQLite donde se van a persistir todas las tablas del proyecto
"""

CARPETA_DATOS = Path("data")
RUTA_BD       = Path("nuclear_outages.db")


"""
Función encontrar_parquet — recibe un patrón de búsqueda (string con wildcard *)
y regresa el Path del archivo .parquet más reciente que coincida dentro de CARPETA_DATOS.
Usa glob() para encontrar todos los archivos que encajen con el patrón y sorted()
para ordenarlos alfabéticamente, quedándose con el último (el más reciente por nombre).
Si no encuentra ningún archivo lanza FileNotFoundError para que el error sea explícito
y no se propague silenciosamente al resto del pipeline.
"""

def encontrar_parquet(patron: str) -> Path:
    archivos = sorted(CARPETA_DATOS.glob(patron))
    if not archivos:
        raise FileNotFoundError(f"No se encontró archivo con patrón: {patron}")
    return archivos[-1]

"""
Función insertar_units — recibe la conexión activa a SQLite y el DataFrame de referencia.
Su responsabilidad es registrar en la tabla 'units' las unidades de medida que aplican
a todo el dataset (megawatts para capacity y outage, percent para percentOutage).
Primero intenta leer cada unidad desde las columnas del DataFrame; si no existen
usa los valores default para no romper la inserción.
Hace commit inmediato, loguea el id autoincremental generado por SQLite y lo regresa
porque todas las demás tablas lo necesitan como llave foránea (units_id).
"""

def insertar_units(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    cursor = conn.execute(
        "INSERT INTO units (capacity_units, outage_units, percentOutage_units) VALUES (?, ?, ?)",
        (
            df["capacity-units"].iloc[0]      if "capacity-units"      in df.columns else "megawatts",
            df["outage-units"].iloc[0]         if "outage-units"        in df.columns else "megawatts",
            df["percentOutage-units"].iloc[0]  if "percentOutage-units" in df.columns else "percent",
        ),
    )
    conn.commit()
    units_id = cursor.lastrowid
    logger.info("units — id=%d", units_id)
    return units_id

"""
Función cargar_us_nuclear — carga las salidas nucleares agregadas a nivel nacional.
Localiza el .parquet correspondiente con encontrar_parquet, lo lee con pandas
y normaliza la columna 'period' a formato YYYY-MM-DD para consistencia con las demás tablas.
Agrega units_id como llave foránea, selecciona solo las columnas necesarias
y los inserta en la tabla 'us_nuclear_outages' usando to_sql con if_exists='append'
para no sobreescribir datos previos si la tabla ya existe.
"""

def cargar_us_nuclear_outages(conn: sqlite3.Connection, units_id: int) -> None:
    ruta = encontrar_parquet("nuclear_us-nuclear-outages_*.parquet")
    df = pd.read_parquet(ruta)
    df["units_id"] = units_id
    df["period"] = pd.to_datetime(df["period"]).dt.strftime("%Y-%m-%d")
    df = df[["period", "capacity", "outage", "percentOutage", "units_id"]]
    df.to_sql("us_nuclear_outages", conn, if_exists="append", index=False)
    logger.info("us_nuclear_outages — %d registros", len(df))


"""
Función cargar_facility_nuclear — carga las salidas desglosadas por instalación nuclear.
Igual que cargar_us_nuclear normaliza 'period' y agrega units_id, pero además conserva
las columnas 'facility' y 'facilityName' que identifican cada planta.
Esta tabla es importante porque actúa como catálogo: la función cargar_generator_nuclear
la consulta para resolver el facility_id de cada generador mediante un JOIN.
Los datos se insertan en la tabla 'facility_nuclear' con modo append.
"""

def cargar_facility_nuclear_outages(conn: sqlite3.Connection, units_id: int) -> None:
    ruta = encontrar_parquet("nuclear_facility-nuclear-outages_*.parquet")
    df = pd.read_parquet(ruta)
    df["units_id"] = units_id
    df["period"] = pd.to_datetime(df["period"]).dt.strftime("%Y-%m-%d")
    df = df[["period", "facility", "facilityName", "capacity", "outage", "percentOutage", "units_id"]]
    df.to_sql("facility_nuclear_outages", conn, if_exists="append", index=False)
    logger.info("facility_nuclear_outages — %d registros", len(df))

"""
Función cargar_generator_nuclear — carga las salidas al nivel más granular: por generador.
Después de leer y normalizar el .parquet, convierte 'facility' a string en ambos DataFrames
para evitar errores de tipo al hacer el merge (por ejemplo int vs str).
Hace un LEFT JOIN contra la tabla 'facility_nuclear_outages' ya cargada en la BD,
usando 'facility' y 'period' como llaves compuestas para obtener el facility_id.
El LEFT JOIN garantiza que ningún generador se pierda aunque no encuentre su facility;
esos casos quedarán con facility_id = NULL para revisión posterior.
Finalmente inserta el DataFrame enriquecido en la tabla 'generator_nuclear'.
"""
def cargar_generator_nuclear_outages(conn: sqlite3.Connection, units_id: int) -> None:
    ruta = encontrar_parquet("nuclear_generator-nuclear-outages_*.parquet")
    df_gen = pd.read_parquet(ruta)
    df_gen["period"] = pd.to_datetime(df_gen["period"]).dt.strftime("%Y-%m-%d")
    df_gen["facility"] = df_gen["facility"].astype(str)

    # Leemos facility_nuclear desde la BD para obtener los ids ya asignados por SQLite
    df_fac = pd.read_sql("SELECT id, facility, period FROM facility_nuclear_outages", conn)
    df_fac["facility"] = df_fac["facility"].astype(str)

    df_merged = df_gen.merge(df_fac, on=["facility", "period"], how="left").rename(columns={"id": "facility_id"})
    df_merged["units_id"] = units_id
    df_merged = df_merged[["period", "facility_id", "facilityName", "generator", "capacity", "outage", "percentOutage", "units_id"]]
    df_merged.to_sql("generator_nuclear_outages", conn, if_exists="append", index=False)
    logger.info("generator_nuclear_outages — %d registros", len(df_merged))

"""
Función guardar_analisis — inserta el diccionario de métricas en la tabla 'analytics'
de la base de datos SQLite indicada en ruta_bd.
Serializa todo el diccionario como JSON en la columna 'resultado' para no perder
información detallada (tendencias, top10, promedios).
Usa try/except para que un fallo al guardar el análisis no detenga el pipeline principal.
"""
def guardar_analisis(analisis: dict, ruta_bd: Path) -> None:
    if not analisis:
        logger.warning("No hay análisis para guardar")
        return
    try:
        conn = sqlite3.connect(ruta_bd)
        conn.execute(
            """
            INSERT INTO analytics (endpoint, periodo_inicio, periodo_fin, total_registros, resultado, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                analisis["endpoint"],
                analisis.get("periodo_inicio"),
                analisis.get("periodo_fin"),
                analisis.get("total_registros"),
                json.dumps(analisis, default=str),
                datetime.now(timezone.utc).isoformat(),
            )
        )
        conn.commit()
        conn.close()
        logger.info("Análisis guardado en BD")
    except Exception as e:
        logger.warning(f"No se pudo guardar análisis en BD: {e}")

"""
Bloque principal — se ejecuta solo cuando el script se corre directamente (no al importarlo).
Abre la conexión a nuclear.db (la crea si no existe), lee el parquet nacional como referencia
para extraer las unidades de medida, inserta el registro en 'units' y con el id resultante
dispara las tres funciones de carga en orden: nacional → por instalación → por generador.
El orden importa porque generator depende de facility para el JOIN.
"""
if __name__ == "__main__":
    logger.info("Conectando a %s", RUTA_BD)
    with sqlite3.connect(RUTA_BD) as conn:
        ruta_us  = encontrar_parquet("nuclear_us-nuclear-outages_*.parquet")
        df_ref   = pd.read_parquet(ruta_us)
        units_id = insertar_units(conn, df_ref)

        cargar_us_nuclear_outages(conn, units_id)
        cargar_facility_nuclear_outages(conn, units_id)
        cargar_generator_nuclear_outages(conn, units_id)

    logger.info("Datos cargados correctamente en %s", RUTA_BD)