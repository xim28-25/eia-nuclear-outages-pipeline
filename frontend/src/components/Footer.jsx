import { FaGithub } from "react-icons/fa";
import { CiLinkedin } from "react-icons/ci";
import LogoBlanco from "../assets/img/ArkhamLogoBlanco.png"

/**
 * Componente Footer — Pie de página de la aplicación.
 * Contiene la identidad de marca, créditos de autoría y enlaces sociales.
 * Utiliza un diseño flexbox responsivo que se adapta de columna (móvil) a fila (desktop).
 */
export default function Footer() {
  

  // Clase base para los botones sociales con efectos de glassmorphism y micro-interacciones
  const linkCls = "flex items-center gap-1.5 px-3 py-3 rounded-full border border-white/10 bg-white/5 text-slate-300 text-[12px] font-semibold transition-all duration-200 hover:text-white hover:border-white/20 hover:bg-white/10 hover:shadow-sm hover:-translate-y-px no-underline"

  return (
    <footer className="w-full mt-20 border-t border-white/10 bg-slate-900">
      
      <div className="max-w-[1350px] mx-auto px-6 py-8 flex flex-col md:flex-row items-center justify-between gap-6">
        
        {/*  LOGO  ARKHAM (BLANCO) */}
        <div className="flex items-center gap-2.5">
           <img src={LogoBlanco} alt="Arkham Logo" className="w-10 h-8" />
                <span className="text-xl font-bold text-white tracking-tight" style={{ fontFamily: "'DM Serif Display', serif" }}>
                  Arkham
                </span>
         </div>

        {/* CRÉDITOS */}
        <div className="text-center md:text-left">
          <p className="font-semibold text-white text-[15px] tracking-tight">
            Ximena Andrade Luviano
          </p>
          <p className="text-[12px] text-slate-400 font-medium mt-1">
            © 2026 Arkham Challenge · Software Engineer
          </p>
          <p className="text-[12px] text-slate-500 font-medium mt-0.5">
            Derechos Reservados
          </p>
        </div>

        {/* REDES SOCIALES (ENLACES EXTERNOS) */}
        {/* Los enlaces utilizan target="_blank" por seguridad y experiencia de usuario */}
        <div className="flex gap-3">
          <a href="https://github.com/xim28-25" target="_blank" rel="noopener noreferrer" className={linkCls}>
            <FaGithub size={32}/>
          </a>
          <a href="https://www.linkedin.com/in/ximena-andrade-luviano-a9905b354" target="_blank" rel="noopener noreferrer" className={linkCls}>
            <CiLinkedin size={32}/>
          </a>
        </div>

      </div>
    </footer>
  )
}