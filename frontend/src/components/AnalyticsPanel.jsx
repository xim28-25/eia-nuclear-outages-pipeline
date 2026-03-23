import CountUp from "react-countup";
import { TrendingUp, Factory, CalendarDays, Hash, Clock, SlidersHorizontal, Inbox } from "lucide-react"

/**
 * Estilos base para tarjetas y etiquetas con Glassmorphism.
 * Mantienen la consistencia visual con el resto de los módulos (Data/Filters).
 */
const cardCls = "bg-white/65 backdrop-blur-xl border border-white/80 rounded-2xl p-5 shadow-[0_2px_20px_rgba(0,0,0,0.04)]"
const labelCls = "text-[10px] font-bold uppercase tracking-widest text-black mb-1.5 flex items-center gap-1.5"

/**
 * Componente AnalyticsPanel — Visualización de métricas y tendencias.
 * Muestra un resumen del dataset, el comportamiento mensual de los outages
 * y un ranking de las plantas con mayor afectación histórica en MW.
 */
export default function AnalyticsPanel({ analytics, analyticsEndpoint, setAnalyticsEndpoint }) {
  return (
    <div className="flex flex-col gap-5">

      {/* SECCIÓN: SELECTOR DE DATASET PARA ANALYTICS */}
      <div className={`${cardCls} py-3.5 flex items-end gap-6`}>
        <div className="flex items-center gap-2 text-white mr-1">
          <SlidersHorizontal size={14} />
          <span className="text-[11px] font-bold uppercase tracking-widest text-black">Dataset</span>
        </div>
        <div>
          <select
            value={analyticsEndpoint}
            onChange={e => setAnalyticsEndpoint(e.target.value)}
            className="bg-white/70 border border-black/[0.08] rounded-xl px-3 py-2 text-[13px] text-black outline-none focus:border-black/20 transition-all min-w-[140px]"
          >
            <option value="us">Nacional</option>
            <option value="facility">Por Planta</option>
            <option value="generator">Por Generador</option>
          </select>
        </div>
      </div>

      {/* MANEJO DE ESTADO VACÍO (Sin datos procesados en la tabla analytics de BD) */}
      {!analytics ? (
        <div className="flex flex-col items-center justify-center py-24 text-slate-400">
          <Inbox size={40} strokeWidth={1.2} className="mb-3 text-slate-300" />
          <p className="text-sm font-medium">No hay analytics disponibles</p>
        </div>
      ) : (
        <>
          {/* TARJETAS DE RESUMEN (KPIs) */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
            {[
              { label: "Total registros", value: analytics.analytics.total_registros, isCount: true, Icon: Hash },
              { label: "Período inicio",  value: analytics.analytics.periodo_inicio?.slice(0, 10), Icon: CalendarDays },
              { label: "Período fin",     value: analytics.analytics.periodo_fin?.slice(0, 10), Icon: CalendarDays },
              { label: "Actualizado",     value: analytics.created_at?.slice(0, 10), Icon: Clock },
            ].map(({ label, value, Icon }) => (
              <div key={label} className={cardCls}>
                <p className={labelCls}>
                  <Icon size={11}  className="text-white"/>
                  {label}
                </p>
                <p className="text-lg font-bold text-black tracking-tight" style={{ fontFamily: "'DM Serif Display', serif" }}>
                  {value}
                </p>
              </div>
            ))}
          </div>

          {/* TENDENCIA MENSUAL (TABLA + MINI BARRAS) */}
          {/* Solo se muestra si el objeto contiene datos de tendencia (Dataset Nacional) */}
          {analytics.analytics.tendencia_mensual && (
            <div className={cardCls}>
              <h2 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-black mb-4">
                <TrendingUp size={14} />
                Tendencia mensual de outage (%)
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-[12px]">
                  <thead>
                    <tr>
                      {["Mes", "% Outage", "Visualización"].map(h => (
                        <th key={h} className="text-left px-2 py-1.5 text-[10px] font-bold uppercase tracking-widest text-white">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {/* Mostramos solo los últimos 24 meses para no saturar la vista */}
                    {Object.entries(analytics.analytics.tendencia_mensual)
                      .slice(-24)
                      .map(([mes, valor]) => (
                        <tr key={mes} className="border-t border-black/[0.04] hover:bg-black/[0.02]">
                          <td className="px-2 py-1.5 text-slate-500 font-medium">{mes}</td>
                          <td className="px-2 py-1.5 text-black font-bold font-mono">{valor}%</td>
                          <td className="px-2 py-1.5 w-48">
                            <div className="bg-slate-100 rounded-full h-1.5">
                              {/* Barra de progreso dinámica escalada para mayor visibilidad */}
                              <div
                                className="bg-black h-1.5 rounded-full transition-all duration-500"
                                style={{ width: `${Math.min(valor * 3, 100)}%` }}
                              />
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* RANKING TOP 10 (MAYOR IMPACTO MW) */}
          {analytics.analytics.top10_plantas_mayor_outage_historico_MW && (
            <div className={cardCls}>
              <h2 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-black mb-4">
                <Factory size={14} className="text-white" />
                Top 10 plantas — mayor outage histórico (MW)
              </h2>
              <div className="flex flex-col gap-3">
                {Object.entries(analytics.analytics.top10_plantas_mayor_outage_historico_MW).map(([planta, mw], i) => {
                  // Calculamos el valor máximo para normalizar el ancho de las barras
                  const max = Object.values(analytics.analytics.top10_plantas_mayor_outage_historico_MW)[0]
                  return (
                    <div key={planta} className="flex items-center gap-3">
                      <span className={`text-[11px] font-black w-5 text-center ${i === 0 ? "text-black" : "text-slate-300"}`}>
                        {i + 1}
                      </span>
                      <span className="text-[13px] text-slate-700 font-medium w-44 truncate">
                        {planta}
                      </span>
                      <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                        <div
                          className="bg-black h-1.5 rounded-full transition-all duration-500"
                          style={{ width: `${(mw / max) * 100}%` }}
                        />
                      </div>
                      <span className="text-[12px] font-bold text-black font-mono w-28 text-right">
                        {mw.toLocaleString()} MW
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}