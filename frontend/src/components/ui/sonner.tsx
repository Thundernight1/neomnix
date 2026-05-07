import * as React from "react"
import { Toaster as Sonner } from "sonner"

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-slate-900 group-[.toaster]:text-slate-100 group-[.toaster]:border-slate-800 group-[.toaster]:shadow-lg",
          description: "group-[.toaster]:text-slate-400",
          actionButton:
            "group-[.toaster]:bg-blue-600 group-[.toaster]:text-white",
          cancelButton:
            "group-[.toaster]:bg-slate-800 group-[.toaster]:text-slate-400",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
