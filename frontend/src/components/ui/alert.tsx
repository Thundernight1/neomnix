import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

/**
 * Alert - shadcn-style alert component.
 *
 * Variants:
 *   - default:    neutral surface, useful for informational banners.
 *   - destructive: red accent, used for errors and load failures.
 *
 * The variants are intentionally narrow. The flashing-red critical
 * overlay in Dashboard.tsx is *not* an Alert variant; it is a
 * dedicated full-bleed element with its own animation. An Alert is
 * for static, dismissable banners, not for live telemetry.
 */
const alertVariants = cva(
  "relative w-full rounded-lg border p-4 [&>svg~div]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-slate-100",
  {
    variants: {
      variant: {
        default:
          "border-slate-800 bg-slate-900 text-slate-100 [&>svg]:text-slate-100",
        destructive:
          "border-red-900/50 bg-red-950/30 text-red-100 [&>svg]:text-red-300 [&>svg~div]:text-red-100",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

const Alert = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>
>(({ className, variant, ...props }, ref) => (
  <div
    ref={ref}
    role="alert"
    className={cn(alertVariants({ variant }), className)}
    {...props}
  />
))
Alert.displayName = "Alert"

const AlertTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn("mb-1 font-medium leading-none tracking-tight text-slate-100", className)}
    {...props}
  />
))
AlertTitle.displayName = "AlertTitle"

const AlertDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm text-slate-400 [&_p]:leading-relaxed", className)}
    {...props}
  />
))
AlertDescription.displayName = "AlertDescription"

export { Alert, AlertTitle, AlertDescription }
