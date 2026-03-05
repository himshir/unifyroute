import * as React from "react"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
    checked?: boolean
    onCheckedChange?: (checked: boolean) => void
}

const Checkbox = React.forwardRef<HTMLButtonElement, Omit<CheckboxProps, "onChange">>(
    ({ className, checked = false, onCheckedChange, disabled, ...props }, ref) => (
        <button
            ref={ref}
            type="button"
            role="checkbox"
            aria-checked={checked}
            disabled={disabled}
            onClick={() => onCheckedChange?.(!checked)}
            className={cn(
                "h-4 w-4 shrink-0 rounded-sm border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2",
                "disabled:cursor-not-allowed disabled:opacity-50",
                checked && "bg-violet-600 border-violet-600 text-white",
                className
            )}
            {...(props as any)}
        >
            {checked && <Check size={12} className="text-white" strokeWidth={3} />}
        </button>
    )
)
Checkbox.displayName = "Checkbox"

export { Checkbox }
