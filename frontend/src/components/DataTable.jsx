import { useState } from "react"
import { ArrowUp, ArrowDown, ArrowUpDown, ChevronLeft, ChevronRight, Inbox } from "lucide-react"

/**
 * Componente DataTable — Representación tabular de los registros nucleares.
 * Maneja el ordenamiento local de la página actual y la navegación entre páginas
 * mediante el control del 'offset' que se envía al backend.
 */
export default function DataTable({ data, total, limit, offset, setOffset }) {
  
  // ── ESTADO DE ORDENAMIENTO (LOCAL) ──
  const [sortCol, setSortCol] = useState("period")
  const [sortDir, setSortDir] = useState("desc")

  /** Extracción dinámica de columnas:
   * Filtramos 'units_id' para no mostrar IDs internos que no aportan valor al usuario.
   */
  const columns = data.length > 0
    ? Object.keys(data[0]).filter(k => k !== "units_id")
    : []

  /** Lógica de ordenamiento:
   * Se ejecuta sobre el array 'data' recibido para permitir organizar la vista
   * sin necesidad de realizar una nueva petición al servidor.
   */
  const sorted = [...data].sort((a, b) => {
    if (a[sortCol] < b[sortCol]) return sortDir === "asc" ? -1 : 1
    if (a[sortCol] > b[sortCol]) return sortDir === "asc" ? 1 : -1
    return 0
  })

  // Cambia la columna de orden o invierte la dirección (asc/desc)
  const toggleSort = (col) => {
    if (sortCol === col) setSortDir(d => d === "asc" ? "desc" : "asc")
    else { setSortCol(col); setSortDir("asc") }
  }

  // Renderiza el icono correspondiente según el estado de ordenamiento actual
  const SortIcon = ({ col }) => {
    if (sortCol !== col) return <ArrowUpDown size={11} className="text-slate-300" />
    return sortDir === "asc"
      ? <ArrowUp size={11} className="text-black" />
      : <ArrowDown size={11} className="text-black" />
  }

  // ESTADO VACÍO (EMPTY STATE) 
  if (data.length === 0) return (
    <div className="flex flex-col items-center justify-center py-24 text-slate-400">
      <Inbox size={40} strokeWidth={1.2} className="mb-3 text-slate-300" />
      <p className="text-sm font-medium">No se encontraron registros</p>
    </div>
  )

  // Cálculos para habilitar/deshabilitar navegación
  const canPrev = offset > 0
  const canNext = offset + limit < total

  return (
    <>
      {/* CONTROLES SUPERIORES Y CONTADOR DE REGISTROS */}
      <div className="flex items-center justify-between mt-4 mb-5 ">
        <button
          onClick={() => setOffset(o => Math.max(0, o - limit))}
          disabled={!canPrev}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl border text-[13px] font-semibold transition-all duration-200   ${
            !canPrev
              ? "opacity-30 cursor-not-allowed border-slate-200 text-slate-400"
              : "border-black/10 text-black bg-white/80 hover:bg-white hover:shadow-md hover:-translate-y-px cursor-pointer"
          }`}
        >
          <ChevronLeft size={14} />
          Anterior
        </button>

        {/* Resumen de posición en el dataset total */}
        <p className="text-[12px] text-slate-400 font-medium mb-2.5">
          Mostrando{" "}
          <span className="text-white font-bold">{offset + 1}–{Math.min(offset + limit, total)}</span>
          {" "}de{" "}
          <span className="text-white font-bold">{total.toLocaleString()}</span>
          {" "}registros
        </p>

        <button
          onClick={() => setOffset(o => o + limit)}
          disabled={!canNext}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl border text-[13px] font-semibold transition-all duration-200 cursor-pointer ${
            !canNext
              ? "opacity-30 cursor-not-allowed border-slate-200 text-slate-400"
              : "border-black/10 text-black bg-white/80 hover:bg-white hover:shadow-md hover:-translate-y-px"
          }`}
        >
          Siguiente
          <ChevronRight size={14} />
        </button>
      </div>

      {/*  TABLA DE DATOS  */}
      <div className="overflow-x-auto rounded-2xl border border-black/[0.06] shadow-[0_2px_24px_rgba(0,0,0,0.04)] bg-white/60 backdrop-blur-xl">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="bg-slate-50/80 border-b border-black/[0.06]">
              {columns.map(col => (
                <th
                  key={col}
                  onClick={() => toggleSort(col)}
                  className="px-4 py-3 text-left cursor-pointer select-none group"
                >
                  <div className="flex items-center gap-1.5">
                    <span className={`text-[10px] font-bold uppercase tracking-widest transition-colors ${
                      sortCol === col ? "text-black" : "text-slate-400 group-hover:text-slate-600"
                    }`}>
                      {col}
                    </span>
                    <SortIcon col={col} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* Renderizado de filas con estilos de cebra (striped rows) para mejor legibilidad */}
            {sorted.map((row, i) => (
              <tr
                key={i}
                className={`border-b border-black/[0.04] transition-colors duration-100 hover:bg-black/[0.025] ${
                  i % 2 === 0 ? "bg-white/50" : "bg-slate-50/40"
                }`}
              >
                {columns.map(col => (
                  <td key={col} className="px-4 py-2.5 text-slate-700 whitespace-nowrap font-medium">
                    {row[col]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* PAGINACIÓN INFERIOR */}
      <div className="flex items-center justify-between mt-4">
        <button
          onClick={() => setOffset(o => Math.max(0, o - limit))}
          disabled={!canPrev}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl border text-[13px] font-semibold transition-all duration-200  ${
            !canPrev
              ? "opacity-30 cursor-not-allowed border-slate-200 text-slate-400"
              : "border-black/10 text-black bg-white/80 hover:bg-white hover:shadow-md hover:-translate-y-px  "
          }`}
        >
          <ChevronLeft size={14} />
          Anterior
        </button>

        <span className="text-[13px] text-slate-500 font-medium">
          Página{" "}
          <strong className="text-white">{Math.floor(offset / limit) + 1}</strong>
          {" "}de{" "}
          <strong className="text-white">{Math.ceil(total / limit)}</strong>
        </span>

        <button
          onClick={() => setOffset(o => o + limit)}
          disabled={!canNext}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-xl border text-[13px] font-semibold transition-all duration-200 cursor-pointer ${
            !canNext
              ? "opacity-30 cursor-not-allowed border-slate-200 text-slate-400"
              : "border-black/10 text-black bg-white/80 hover:bg-white hover:shadow-md hover:-translate-y-px"
          }`}
        >
          Siguiente
          <ChevronRight size={14} />
        </button>
      </div>
    </>
  )
}