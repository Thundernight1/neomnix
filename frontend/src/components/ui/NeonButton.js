import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
const neonButtonVariants = cva("inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 relative overflow-hidden group", {
    variants: {
        variant: {
            default: "bg-cyber-cyan text-cyber-navy shadow-none hover:bg-cyber-cyan/90 neon-glow-cyan",
            outline: "border border-cyber-cyan/50 bg-transparent text-cyber-cyan hover:bg-cyber-cyan/10 neon-glow-cyan",
            purple: "bg-cyber-purple text-white shadow-none hover:bg-cyber-purple/90 neon-glow-purple",
            ghost: "hover:bg-accent hover:text-accent-foreground",
        },
        size: {
            default: "h-10 px-4 py-2",
            sm: "h-8 rounded-md px-3 text-xs",
            lg: "h-12 rounded-md px-8 text-base",
            icon: "h-9 w-9",
        },
    },
    defaultVariants: {
        variant: "default",
        size: "default",
    },
});
const NeonButton = React.forwardRef(({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (_jsxs(motion.div, { whileHover: { scale: 1.05 }, whileTap: { scale: 0.95 }, className: "inline-block", children: [_jsx(Comp, { className: cn(neonButtonVariants({ variant, size, className })), ref: ref, ...props }), _jsx("div", { className: "absolute inset-0 bg-gradient-to-tr from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" })] }));
});
NeonButton.displayName = "NeonButton";
export { NeonButton, neonButtonVariants };
