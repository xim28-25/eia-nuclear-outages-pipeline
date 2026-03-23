
-- EIA Nuclear Outages — Esquema y carga de datos
-- Base de datos: SQLite
--
-- Este script define la estructura completa de la base de datos
-- para almacenar las salidas nucleares reportadas por la EIA.
-- Se crean 4 tablas principales más sus índices de consulta.
--
-- Tablas:
--   units  — unidades de medida compartidas por los 3 endpoints
--   us_nuclear_outages — datos nacionales diarios agregados
--   facility_nuclear — datos desglosados por planta
--   generator_nuclear — datos desglosados por generador/reactor
--   analytics — bitácora de resultados por endpoint
--
-- Relaciones (llaves foráneas):
--   us_nuclear_outages.units_id - units.id
--   facility_nuclear.units_id - units.id
--   generator_nuclear.facility_id - facility_nuclear.id
--   generator_nuclear.units_id - units.id
--
-- Uso:
--   sqlite3 nuclear_outages.db < crear_tablas.sql

-- CREACIÓN DE TABLAS
-- Todas usan IF NOT EXISTS para que el script sea idempotente,
-- es decir, se puede correr varias veces sin romper datos existentes.

-- Tabla units — catálogo de unidades de medida.
-- Se inserta una sola fila por carga y su id se usa como llave foránea
-- en las tres tablas de datos para no repetir los strings de unidades
-- en cada registro (normalización básica).
-- En donde: 
-- capacity_uits - "megawatts"
-- outage_units  - "megawatts"
-- percentOutage_units- "percent"
CREATE TABLE IF NOT EXISTS units (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    capacity_units      VARCHAR,   
    outage_units        VARCHAR,   
    percentOutage_units VARCHAR    
);

-- Tabla us_nuclear_outages — datos nacionales diarios.
-- Cada fila representa un día y contiene la capacidad total instalada
-- del parque nuclear de EE.UU., cuánta estaba fuera de servicio y
-- qué porcentaje representa esa salida respecto al total.
-- period es NOT NULL porque sin fecha el registro no tiene sentido temporal.
--En donde:
--capacity: capacidad total instalada (megawatts)
--outage: capacidad fuera de servicio (megawatts)
--percentOutage: porcentaje fuera de servicio
CREATE TABLE IF NOT EXISTS us_nuclear_outages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    period        DATE    NOT NULL,
    capacity      FLOAT,           
    outage        FLOAT,          
    percentOutage FLOAT,           
    units_id      INTEGER REFERENCES units(id)
);

-- Tabla facility_nuclear — datos por planta nuclear.
-- Desglosa la información nacional al nivel de cada instalación.
-- 'facility' guarda el Plant Code oficial de la EIA (entero),
-- que junto con 'period' forma la llave natural de cada registro.
-- Esta tabla sirve además como catálogo para resolver el facility_id
-- en la tabla generator_nuclear al momento de la carga.
--En donde:
--facility: código de planta (Plant code EIA)
--facilityName: nombre legible de la planta
--capacity: capacidad total instalada (megawatts)
-- outage: capacidad fuera de servicio (megawatts)
--percentOutage: porcentaje fuera de servicio
CREATE TABLE IF NOT EXISTS facility_nuclear_outages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    period        DATE    NOT NULL,
    facility      INTEGER NOT NULL, 
    facilityName  VARCHAR,         
    capacity      FLOAT,            
    outage        FLOAT,            
    percentOutage FLOAT,            
    units_id      INTEGER REFERENCES units(id)
);

-- Tabla generator_nuclear — datos por generador o reactor individual.
-- Es la tabla más granular del esquema. Cada fila representa un reactor
-- específico dentro de una planta en una fecha dada.
-- facility_id es FK a facility_nuclear y puede quedar NULL si durante
-- la carga un generador no encuentra su planta correspondiente en el JOIN
-- (esos casos quedan pendientes de revisión).
--En donde:
-- facility_id   es la llave secundaria FK a planta
-- facilityName: nombre de la planta (desnormalizado para consultas rápidas)
-- generator: identificador del reactor/generador
-- capacity: capacidad instalada del reactor (megawatts)
-- outage: capacidad fuera de servicio (megawatts)
-- percentOutage FLOAT: porcentaje fuera de servicio
CREATE TABLE IF NOT EXISTS generator_nuclear_outages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    period        DATE    NOT NULL,
    facility_id   INTEGER REFERENCES facility_nuclear_outages(id),
    facilityName  VARCHAR,          
    generator     VARCHAR,          
    capacity      FLOAT,          
    outage        FLOAT,           
    percentOutage FLOAT,            
    units_id      INTEGER REFERENCES units(id)
);

-- Tabla analytics — bitácora de ejecuciones del pipeline.
-- Registra metadatos de cada carga: qué endpoint se procesó,
-- el rango de fechas cubierto, cuántos registros se insertaron
-- y el resultado de la operación (éxito o descripción del error).
-- created_at permite auditar cuándo se corrió cada proceso.
--En donde_
--resultado: mando 'ok' o descirbe el error
CREATE TABLE IF NOT EXISTS analytics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint         VARCHAR,
    periodo_inicio   DATE,
    periodo_fin      DATE,
    total_registros  INTEGER,
    resultado        TEXT,       
    created_at       DATETIME
);



--CREACIÓN DE ÍNDICES
-- Los índices aceleran las consultas más frecuentes sin modificar
-- los datos. IF NOT EXISTS evita errores si el script se re-ejecuta.
-- Cada índice se crea sobre las columnas que más se usan en WHERE
-- o en los JOINs del pipeline de carga.


-- Índice sobre period en us_nuclear_outages.
-- Útil para consultas que filtran o agrupan por fecha a nivel nacional.
CREATE INDEX IF NOT EXISTS idx_us_period
    ON us_nuclear_outages(period);

-- Índice sobre period en facility_nuclear.
-- Acelera filtros temporales cuando se consultan datos por planta.
CREATE INDEX IF NOT EXISTS idx_facility_period
    ON facility_nuclear_outages(period);

-- Índice sobre facility (Plant code) en facility_nuclear.
-- Necesario para el JOIN que hace cargar_generator_nuclear al buscar
-- el facility_id de cada generador usando el código de planta.
CREATE INDEX IF NOT EXISTS idx_facility_facility
    ON facility_nuclear_outages(facility);

-- Índice sobre period en generator_nuclear.
-- Optimiza consultas temporales al nivel más granular del esquema.
CREATE INDEX IF NOT EXISTS idx_generator_period
    ON generator_nuclear_outages(period);

-- Índice sobre facility_id en generator_nuclear.
-- Acelera los JOINs entre generator_nuclear y facility_nuclear,
-- por ejemplo al consultar todos los reactores de una planta.
CREATE INDEX IF NOT EXISTS idx_generator_facility_id
    ON generator_nuclear_outages(facility_id);