import { Button } from "@/components/ui/button"
import { AlertCircle, ArrowRight } from "lucide-react"

interface ErrorStateProps {
    title?: string
    message?: string
}

export function ErrorState({
    title = "Authentication Error",
    message = "Unable to load data. Your Gateway Token may be missing or invalid. Please configure your token in the Settings."
}: ErrorStateProps) {
    return (
        <div className="flex flex-col items-center justify-center p-12 text-center h-[50vh] animate-in fade-in-50">
            <div className="h-16 w-16 bg-destructive/10 rounded-full flex items-center justify-center mb-6">
                <AlertCircle className="h-8 w-8 text-destructive" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight mb-2">{title}</h2>
            <p className="text-muted-foreground max-w-[500px] mb-8">{message}</p>
            <Button onClick={() => window.location.href = "/settings"} size="lg" className="rounded-full">
                Go to Settings <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
        </div>
    )
}
