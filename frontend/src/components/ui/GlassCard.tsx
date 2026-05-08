import * as React from "react"
import { cn } from "@/lib/utils"
import { motion } from "framer-motion"

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean
}

const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ className, children, hoverEffect = true, ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        whileHover={hoverEffect ? { 
          scale: 1.05, 
          rotateX: 5, 
          rotateY: -5,
          z: 50,
          transition: { type: "spring", stiffness: 300, damping: 20 } 
        } : {}}
        style={{ transformStyle: "preserve-3d" }}
        className={cn(
          "glass-card rounded-2xl p-6 transition-all duration-500 relative",
          "border border-white/10 bg-gradient-to-br from-slate-900/80 to-slate-950/90",
          "shadow-[0_20px_50px_rgba(0,0,0,0.5)] hover:shadow-[0_40px_80px_rgba(0,242,255,0.15)]",
          className
        )}
        {...props}
      >
        <div className="relative z-10" style={{ transform: "translateZ(30px)" }}>{children}</div>
        {/* İç Işıltı */}
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-cyber-cyan/5 via-transparent to-white/5 pointer-events-none" />
      </motion.div>
    )
  }
)
GlassCard.displayName = "GlassCard"

export { GlassCard }
