import { SlidersHorizontal } from "lucide-react"

/**
 * Estilos base reutilizables para los inputs y etiquetas.
 * Se utiliza Glassmorphism (backdrop-blur) y bordes sutiles para 
 * mantener una estética limpia y moderna.
 */
const inputCls = "bg-white/70 border border-black/[0.08] rounded-xl px-3 text-[13px] text-black outline-none focus:border-black/20 focus:ring-2 focus:ring-black/5 transition-all duration-200 min-w-[130px] backdrop-blur-sm"
const labelCls = "block text-[10px] font-bold uppercase tracking-widest text-black mb-1.5"

/**
 * Componente FilterBar — Barra de herramientas para filtrar datos.
 * Permite al usuario conmutar entre datasets (Nacional/Planta/Generador),
 * definir rangos de fecha y controlar el tamaño de la página.
 */
export default function FilterBar({
  endpoint, setEndpoint,
  dateStart, setDateStart,
  dateEnd, setDateEnd,
  limit, setLimit,
  setOffset,
}) {
  return (
    /* CONTENEDOR PRINCIPAL:
       Utiliza un sistema de Grid responsivo que se adapta de 1 a 5 columnas.
       El 'backdrop-blur-xl' crea el efecto de cristal translúcido.
    */
    <div className="bg-white/55 backdrop-blur-xl border border-white/70 rounded-2xl px-6 py-4 mb-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-5 items-end shadow-[0_2px_20px_rgba(0,0,0,0.04)]">
      
      {/* TÍTULO DE SECCIÓN */}
      <div className="flex items-center gap-2 text-black mr-2">
        <SlidersHorizontal size={15} />
        <span className="text-[11px] font-bold uppercase tracking-widest">Filtros</span>
      </div>

      {/* SELECTOR DE DATASET: Cambia el origen de los datos en la API */}
      <div>
        <label className={labelCls}>Dataset</label>
        <select
          value={endpoint}
          onChange={e => { setEndpoint(e.target.value); setOffset(0) }}
          className={inputCls}
        >
          <option value="us">Nacional</option>
          <option value="facility">Por Planta</option>
          <option value="generator">Por Generador</option>
        </select>
      </div>

      {/* FILTRO: FECHA DE INICIO */}
      <div>
        <label className={labelCls}>Fecha inicio</label>
        <input
          type="date"
          value={dateStart}
          onChange={e => { setDateStart(e.target.value); setOffset(0) }}
          className={inputCls}
        />
      </div>

      {/* FILTRO: FECHA DE FIN */}
      <div>
        <label className={labelCls}>Fecha fin</label>
        <input
          type="date"
          value={dateEnd}
          onChange={e => { setDateEnd(e.target.value); setOffset(0) }}
          className={inputCls}
        />
      </div>

      {/* CONTROL DE PAGINACIÓN: Define cuántos registros mostrar por página */}
      <div>
        <label className={labelCls}>Registros</label>
        <select
          value={limit}
          onChange={e => { setLimit(Number(e.target.value)); setOffset(0) }}
          className={inputCls}
        >
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </div>
    </div>
  )
}