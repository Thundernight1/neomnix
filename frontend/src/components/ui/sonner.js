import { jsx as _jsx } from "react/jsx-runtime";
import { Toaster as Sonner } from "sonner";
const Toaster = ({ ...props }) => {
    return (_jsx(Sonner, { className: "toaster group", toastOptions: {
            classNames: {
                toast: "group toast group-[.toaster]:bg-slate-900 group-[.toaster]:text-slate-100 group-[.toaster]:border-slate-800 group-[.toaster]:shadow-lg",
                description: "group-[.toaster]:text-slate-400",
                actionButton: "group-[.toaster]:bg-blue-600 group-[.toaster]:text-white",
                cancelButton: "group-[.toaster]:bg-slate-800 group-[.toaster]:text-slate-400",
            },
        }, ...props }));
};
export { Toaster };
