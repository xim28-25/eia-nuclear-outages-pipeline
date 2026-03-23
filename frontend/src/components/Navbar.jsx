import { useState, useEffect } from "react"
import { RefreshCw, Database, BarChart2 } from "lucide-react"
import Logo from "../assets/img/ArkhamLogo.png"
import { FiCheck } from "react-icons/fi";

/**
 * Componente Navbar — Navegación principal de la aplicación.
 * Controla el cambio de pestañas (Data/Analytics) y el disparador del pipeline.
 * Implementa un efecto de scroll para cambiar su apariencia dinámicamente.
 */
export default function Navbar({ tab, setTab, onRefresh, refreshLoading, refreshMsg }) {
  const [scrolled, setScrolled] = useState(false)

  // Detecta el desplazamiento vertical para aplicar estilos de vidrio (glassmorphism)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener("scroll", onScroll)
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 h-16 flex items-center justify-between px-8 transition-all duration-300 ${
      scrolled
        ? "bg-white/80 backdrop-blur-xl border-b border-black/[0.07] shadow-[0_2px_20px_rgba(0,0,0,0.06)]"
        : "bg-gray-100/85 backdrop-blur-md border-b border-white/50"
    }`}>

      {/*  LOGO (ARKHAM) */}
      <div className="flex items-center gap-2.5">
        <img src={Logo} alt="Arkham Logo" className="w-9 h-8" />
        <span className="text-xl font-bold text-black tracking-tight" style={{ fontFamily: "'DM Serif Display', serif" }}>
          Arkham
        </span>
      </div>

      {/* SELECTOR DE PESTAÑAS (TABS) */}
      {/* Mapeo de navegación para mantener el código DRY y facilitar nuevos módulos */}
      <div className="flex gap-1 bg-slate-900 text-white shadow-sm rounded-xl p-1 ">
        {[
          { key: "data", label: "Data", Icon: Database },
          { key: "analytics", label: "Analytics", Icon: BarChart2 },
        ].map(({ key, label, Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-5 py-1.5 rounded-[9px] text-[13px] font-semibold transition-all duration-200 cursor-pointer ${
              tab === key
                ? "bg-white text-black shadow-sm"
                : "text-slate-300 hover:text-white"
            }`}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* ACCIONES Y ESTADO DEL PIPELINE (REFRESH) */}
      <div className="flex items-center gap-3">
        {refreshMsg && (
          <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 animate-pulse">
            <FiCheck />
            {refreshMsg}
            </span>
        )}
        
        <button
          onClick={onRefresh}
          disabled={refreshLoading}
          className={`flex items-center gap-2 px-4 py-[7px] rounded-xl text-[13px] font-semibold border transition-all duration-200 cursor-pointer ${
            refreshLoading
              ? "opacity-50 cursor-not-allowed bg-slate-50 border-slate-200 text-slate-400 "
              : "bg-white/80 border-black/10 text-black hover:bg-slate-900 hover:text-white hover:border-black/20 hover:shadow-md hover:-translate-y-px active:translate-y-0"
          }`}
        >
          {/* Icono animado durante la sincronización activa con el backend */}
          <RefreshCw size={13} className={refreshLoading ? "animate-spin" : ""} />
          {refreshLoading ? "Syncing..." : "Refresh"}
        </button>
      </div>
    </nav>
  )
}