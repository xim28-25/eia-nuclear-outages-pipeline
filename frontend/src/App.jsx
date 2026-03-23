import { useState, useEffect } from "react"
import { AlertCircle } from "lucide-react"
import Navbar from "./components/Navbar"
import FilterBar from "./components/FilterBar"
import DataTable from "./components/DataTable"
import AnalyticsPanel from "./components/AnalyticsPanel"
import Footer from "./components/Footer"
import { LuLoader } from "react-icons/lu";

/**
 * URL base para las peticiones al backend de Django.
 * Se asume que el servidor corre localmente en el puerto 8000.
 */
const urlBase = "http://127.0.0.1:8000/api"

export default function App() {
  const [pestanaActiva, setPestanaActiva] = useState("data")

  // ESTADO DE DATOS (TABLA PRINCIPAL) 
  const [registros,        setRegistros]        = useState([])
  const [totalRegistros,   setTotalRegistros]   = useState(0)
  const [cargando,         setCargando]         = useState(false)
  const [errorMsg,         setErrorMsg]         = useState(null)
  const [mensajeRefresh,   setMensajeRefresh]   = useState(null)
  const [cargandoRefresh,  setCargandoRefresh]  = useState(false)

  // FILTROS Y PAGINACIÓN 
  const [endpointActivo, setEndpointActivo] = useState("us")
  const [fechaInicio,    setFechaInicio]    = useState("")
  const [fechaFin,       setFechaFin]       = useState("")
  const [limite,         setLimite]         = useState(50)
  const [desplazamiento, setDesplazamiento] = useState(0)

  //  ESTADO DE ANALYTICS (GRÁFICAS) 
  const [datosAnalitica,        setDatosAnalitica]        = useState(null)
  const [cargandoAnalitica,     setCargandoAnalitica]     = useState(false)
  const [endpointAnalitica,     setEndpointAnalitica]     = useState("us")

  /**
   * Función obtenerDatos — construye la query string basándose en los filtros 
   * activos y realiza la petición GET al endpoint /data del backend.
   * Actualiza los registros y el total para la paginación.
   */
  const obtenerDatos = async (mostrarCargando = true) => {
    if (mostrarCargando) setCargando(true);
    setErrorMsg(null);

    try {
      const parametros = new URLSearchParams({
        endpoint: endpointActivo,
        limit: limite,
        offset: desplazamiento,
        ...(fechaInicio && { date_start: fechaInicio }),
        ...(fechaFin    && { date_end:   fechaFin   }),
      });

      const respuesta = await fetch(`${urlBase}/data?${parametros}`);
      
      if (!respuesta.ok) throw new Error(`Error ${respuesta.status}`);
      
      const json = await respuesta.json();

      /* Actualizamos los estados con los registros recuperados.
         Si el pipeline de fondo está corriendo, estos datos cambiarán en cada fetch.
      */
      setRegistros(json.data);
      setTotalRegistros(json.total);

    } catch (e) {
      setErrorMsg("Error al obtener los datos: " + e.message);
    } finally {
      if (mostrarCargando) setCargando(false);
    }
  };

  /**
   * Función obtenerAnalitica — consulta el último análisis procesado 
   * (tendencias y top 10) guardado en la tabla 'analytics' de la base de datos.
   */
  const obtenerAnalitica = async (ep = endpointAnalitica) => {
    setCargandoAnalitica(true)
    setDatosAnalitica(null)
    try {
      const respuesta = await fetch(`${urlBase}/analytics?endpoint=${ep}`)
      if (!respuesta.ok) throw new Error(`Error ${respuesta.status}`)
      const json = await respuesta.json()
      setDatosAnalitica(json)
    } catch (e) {
      setErrorMsg(e.message)
    } finally {
      setCargandoAnalitica(false)
    }
  }

  /**
   * Función manejarRefresh — dispara el pipeline de descarga de la EIA.
   * Debido al volumen de datos (~700k), implementa un AbortController de 8s:
   * si el servidor no responde en ese tiempo, asumimos que el proceso ya pasó 
   * a ejecutarse en el "hilo de fondo" de Django y liberamos la interfaz.
   */
  const manejarRefresh = async () => {
    setCargandoRefresh(true)
    setMensajeRefresh(null)
    setErrorMsg(null)
    
    const controlador = new AbortController()
    const idTimeout   = setTimeout(() => controlador.abort(), 8000)

    try {
      const respuesta = await fetch(`${urlBase}/refresh`, {
        method: "POST",
        signal: controlador.signal,
      })
      clearTimeout(idTimeout)
      
      if (!respuesta.ok) throw new Error(`Error ${respuesta.status}`)
      const json = await respuesta.json()
      setMensajeRefresh(json.message || "Actualizado")
    } catch (e) {
      clearTimeout(idTimeout)
      if (e.name === "AbortError") {
        setMensajeRefresh("Pipeline corriendo en background...")
      } else {
        setErrorMsg("No se pudo conectar con el servidor")
      }
    } finally {
      setCargandoRefresh(false)
      setTimeout(() => obtenerDatos(), 3000)
    }
  }

  /**
   * EFECO: Re-fetch automático de datos cuando cambia cualquier filtro o la página.
   */
  useEffect(() => { 
    obtenerDatos() 
  }, [endpointActivo, fechaInicio, fechaFin, limite, desplazamiento])

  /**
   * EFECTO: Carga los analytics solo si el usuario entra a la pestaña 
   * correspondiente o cambia el endpoint de análisis.
   */
  useEffect(() => { 
    if (pestanaActiva === "analytics") obtenerAnalitica() 
  }, [pestanaActiva, endpointAnalitica])

  return (
    <div className="min-h-screen bg-slate-900/90">
      {/* Fuentes tipográficas para el diseño DM Serif y DM Sans */}
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@500;600&display=swap"
        rel="stylesheet"
      />

      <Navbar
        tab={pestanaActiva}
        setTab={setPestanaActiva}
        onRefresh={manejarRefresh}
        refreshLoading={cargandoRefresh}
        refreshMsg={mensajeRefresh}
      />

      <main className="max-w-7xl mx-auto px-4 pt-24 pb-10">

        {/* Encabezado Principal */}
        <div className="mb-5">
          <h1
            className="text-4xl font-bold text-white tracking-tight leading-tight mb-2 justify-center text-center"
            style={{ fontFamily: "'DM Serif Display', serif" }}
          >
            Nuclear Outages Explorer
          </h1>
          <p className="text-slate-400 text-sm font-medium leading-relaxed justify-center text-center">
            Explora los datos de salidas nucleares de la API EIA.
            Filtra por dataset nacional, planta o generador, rango de fechas y número de registros.
          </p>
        </div>

        {/* Sección de alertas de error global */}
        {errorMsg && (
          <div className="flex items-center gap-2.5 bg-red-50/80 border border-red-200/60 rounded-2xl px-4 py-3 mb-5 backdrop-blur-sm">
            <AlertCircle size={15} className="text-red-500 flex-shrink-0" />
            <span className="text-sm text-red-600 font-medium">{errorMsg}</span>
          </div>
        )}

        {/* RENDERIZADO CONDICIONAL DE PESTAÑAS */}
        
        {/* DATA EXPLORER */}
        {pestanaActiva === "data" && (
          <>
            <FilterBar
              endpoint={endpointActivo}   setEndpoint={setEndpointActivo}
              dateStart={fechaInicio}      setDateStart={setFechaInicio}
              dateEnd={fechaFin}           setDateEnd={setFechaFin}
              limit={limite}               setLimit={setLimite}
              setOffset={setDesplazamiento}
            />

            {cargando ? (
              <div className="flex flex-col items-center justify-center py-24 text-slate-400">
                <LuLoader size={36} strokeWidth={1.2} className="mb-3 animate-spin text-slate-300" />
                <p className="text-sm font-medium">Cargando datos...</p>
              </div>
            ) : (
              <DataTable
                data={registros}
                total={totalRegistros}
                limit={limite}
                offset={desplazamiento}
                setOffset={setDesplazamiento}
              />
            )}
          </>
        )}

        {/* ANALYTICS PANEL */}
        {pestanaActiva === "analytics" && (
          cargandoAnalitica ? (
            <div className="flex flex-col items-center justify-center py-24 text-slate-400">
              <LuLoader size={36} strokeWidth={1.2} className="mb-3 animate-spin text-slate-300" />
              <p className="text-sm font-medium">Cargando analytics...</p>
            </div>
          ) : (
            <AnalyticsPanel
              analytics={datosAnalitica}
              analyticsEndpoint={endpointAnalitica}
              setAnalyticsEndpoint={setEndpointAnalitica}
            />
          )
        )}

      </main>
      <Footer />
    </div>
  )
}