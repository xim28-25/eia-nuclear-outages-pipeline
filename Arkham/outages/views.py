from django.shortcuts import render

import os
import subprocess
import sqlite3
import logging
from pathlib import Path
import threading

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

DB_PATH = Path(__file__).resolve().parent.parent / "nuclear_outages.db"

logger = logging.getLogger(__name__)


"""
Función get_db — abre y retorna una conexión a la base de datos SQLite ubicada en DB_PATH.
Configura row_factory como sqlite3.Row para que cada fila se comporte como un diccionario,
permitiendo acceder a los campos por nombre en lugar de por índice.
"""
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


"""
Función ejecutar_proceso_fondo — envuelve la ejecución de los scripts de descarga
y procesamiento de datos. Se ejecuta en un hilo separado para evitar que Django
bloquee la respuesta HTTP mientras se descargan los registros de la EIA.
"""
def ejecutar_proceso_fondo():
    base = Path(__file__).resolve().parent.parent
    
    try:
        # Ejecuta dataConnector.py para descargar datos de la API
        subprocess.run(
            ["python", str(base / "dataConnector.py")],
            check=True, capture_output=True, text=True
        )

        # Ejecuta dataModel.py para procesar archivos y cargar la DB
        subprocess.run(
            ["python", str(base / "dataModel.py")],
            check=True, capture_output=True, text=True
        )
        
        logger.info("### Proceso de fondo completado exitosamente ###")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error en script de fondo: {e.stderr}")
    except Exception as e:
        logger.error(f"Error inesperado en hilo: {e}")


"""
Vista data — endpoint GET /api/data que consulta una de las tres tablas de salidas nucleares.
Acepta los parámetros opcionales:
  ?endpoint=us|facility|generator  — define qué tabla consultar (default: us).
  ?date_start=YYYY-MM-DD — filtra registros desde esta fecha.
  ?date_end=YYYY-MM-DD — filtra registros hasta esta fecha.
  ?limit=100 — cantidad máxima de registros a retornar (default: 100).
  ?offset=0 — desplazamiento para paginación (default: 0).
Construye la query dinámicamente según los filtros recibidos, ejecuta un COUNT para la
paginación y retorna los resultados junto con el total, límite y offset actuales.
Retorna 400 si el endpoint es inválido y 500 si ocurre un error en la base de datos.
"""
@api_view(["GET"])
def data(request):
    endpoint = request.GET.get("endpoint", "us")
    date_start = request.GET.get("date_start")
    date_end = request.GET.get("date_end")
    limit = int(request.GET.get("limit", 100))
    offset = int(request.GET.get("offset", 0))

    tablas = {
        "us": "us_nuclear_outages",
        "facility":  "facility_nuclear_outages",
        "generator": "generator_nuclear_outages",
    }

    tabla = tablas.get(endpoint)
    if not tabla:
        return Response(
            {"error": f"Endpoint inválido. Usa: {list(tablas.keys())}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    query  = f"SELECT * FROM {tabla} WHERE 1=1"
    params = []

    if date_start:
        query += " AND period >= ?"
        params.append(date_start)
    if date_end:
        query += " AND period <= ?"
        params.append(date_end)

    count_query = f"SELECT COUNT(*) FROM {tabla} WHERE 1=1"
    if date_start:
        count_query += " AND period >= ?"
    if date_end:
        count_query += " AND period <= ?"

    query += " ORDER BY period DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        conn = get_db()
        total = conn.execute(count_query, params[:-2] if params else []).fetchone()[0]
        rows  = conn.execute(query, params).fetchall()
        conn.close()

        return Response({
            "endpoint": endpoint,
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [dict(row) for row in rows],
        })

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


"""
Vista refresh — endpoint POST /api/refresh que dispara la actualización completa de datos.
Inicia un hilo daemon para ejecutar dataConnector.py y dataModel.py en segundo plano,
permitiendo que la API responda de inmediato con un status 202. Esto evita el bloqueo
del navegador y los errores de timeout (504) causados por descargas extensas.
Retorna 202 si el hilo se lanza correctamente, o 500 si ocurre un error al iniciar.
"""
@api_view(["POST"])
def refresh(request):
    try:
        # Se lanza la tarea pesada en un hilo separado para liberar la respuesta HTTP
        hilo = threading.Thread(target=ejecutar_proceso_fondo)
        hilo.daemon = True
        hilo.start()

        return Response({
            "status": "ok", 
            "message": "Los datos se estan procesanco"
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        return Response(
            {"error": "No se pudo iniciar la actualización", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


"""
Vista analytics — endpoint GET /api/analytics que retorna el último resultado de análisis
almacenado en la tabla 'analytics' de la base de datos para el endpoint solicitado.
Acepta el parámetro opcional:
  ?endpoint=us|facility|generator  — define qué análisis consultar (default: us).
Normaliza los alias cortos (us, facility, generator) a sus nombres completos
(us-nuclear-outages, facility-nuclear-outages, generator-nuclear-outages) antes de consultar.
Retorna el JSON del análisis junto con la fecha de creación del registro.
Retorna 400 si el endpoint es inválido, 404 si no hay analytics disponibles aún,
y 500 si ocurre un error inesperado en la base de datos.
"""
@api_view(["GET"])
def analytics(request):
    endpoint = request.GET.get("endpoint", "us")

    endpoints_validos = ["us-nuclear-outages", "facility-nuclear-outages", "generator-nuclear-outages"]

    mapeo = {
        "us":        "us-nuclear-outages",
        "facility":  "facility-nuclear-outages",
        "generator": "generator-nuclear-outages",
    }
    endpoint = mapeo.get(endpoint, endpoint)

    if endpoint not in endpoints_validos:
        return Response(
            {"error": f"Endpoint inválido. Usa: us, facility, generator"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        conn  = get_db()
        row   = conn.execute(
            "SELECT resultado, created_at FROM analytics WHERE endpoint = ? ORDER BY id DESC LIMIT 1",
            (endpoint,)
        ).fetchone()
        conn.close()

        if not row:
            return Response(
                {"error": "No hay analytics disponibles. Corre el pipeline primero."},
                status=status.HTTP_404_NOT_FOUND
            )

        import json
        return Response({
            "endpoint":   endpoint,
            "created_at": row["created_at"],
            "analytics":  json.loads(row["resultado"]),
        })

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )