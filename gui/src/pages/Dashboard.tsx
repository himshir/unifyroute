import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer, BarChart, Bar
} from 'recharts'
import { Activity, DollarSign, Zap, AlertTriangle, TrendingUp, RefreshCw } from "lucide-react"
import { useLogStats, useLogsTimeline, useUsageStats, useCredentials } from "@/lib/api"
import { ErrorState } from "@/components/error-state"
import { Button } from "@/components/ui/button"

const PROVIDER_COLORS: Record<string, string> = {
    openai: "#10b981",
    anthropic: "#f59e0b",
    google: "#3b82f6",
    "google-antigravity": "#6366f1",
    groq: "#ec4899",
    mistral: "#8b5cf6",
    cohere: "#14b8a6",
    together: "#f97316",
    default: "#94a3b8",
}

function providerColor(name: string) {
    return PROVIDER_COLORS[name?.toLowerCase()] ?? PROVIDER_COLORS.default
}

export function Dashboard() {
    const [hours, setHours] = useState(24)
    const { stats, isLoading: statsLoading, isError: statsError, mutate: refetchStats } = useLogStats(hours)
    const { timeline, isLoading: timelineLoading, mutate: refetchTimeline } = useLogsTimeline(hours)
    const { usage, totalCost, isLoading: usageLoading } = useUsageStats(1) // today
    const { credentials } = useCredentials()

    const isLoading = statsLoading || timelineLoading
    if (statsError) return <ErrorState />

    // Build low-quota alerts from credentials that have expires_at soon or low quota
    const expiringCreds = Array.isArray(credentials)
        ? credentials.filter((c: any) => {
            if (!c.expires_at) return false
            const expiresAt = new Date(c.expires_at)
            const hoursLeft = (expiresAt.getTime() - Date.now()) / 3600000
            return hoursLeft < 12 && hoursLeft > 0
        })
        : []

    function refresh() {
        refetchStats()
        refetchTimeline()
    }

    const totalTokens = (stats?.total_prompt_tokens || 0) + (stats?.total_completion_tokens || 0)
    const todayCostDisplay = usageLoading ? "..." : `$${totalCost.toFixed(4)}`

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-end justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
                    <p className="text-muted-foreground pt-1">Overview of LLM Gateway performance.</p>
                </div>
                <div className="flex items-center gap-2">
                    {[6, 24, 48].map(h => (
                        <Button
                            key={h}
                            variant={hours === h ? "default" : "outline"}
                            size="sm"
                            onClick={() => setHours(h)}
                        >
                            {h}h
                        </Button>
                    ))}
                    <Button variant="outline" size="sm" onClick={refresh}>
                        <RefreshCw className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Low-quota / expiring token alerts */}
            {expiringCreds.length > 0 && (
                <div className="space-y-2">
                    {expiringCreds.map((c: any) => (
                        <div
                            key={c.id}
                            className="flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 px-4 py-3 text-sm"
                        >
                            <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                            <span className="text-amber-800 dark:text-amber-300">
                                <span className="font-semibold">{c.label}</span> — OAuth token expires{" "}
                                {new Date(c.expires_at).toLocaleString()}
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {/* Stats cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Requests</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {isLoading ? "..." : (stats?.total_requests ?? 0).toLocaleString()}
                        </div>
                        <p className="text-xs text-muted-foreground">Last {hours} hours</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Tokens Used</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {isLoading ? "..." : totalTokens.toLocaleString()}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            {(stats?.total_prompt_tokens ?? 0).toLocaleString()} in /{" "}
                            {(stats?.total_completion_tokens ?? 0).toLocaleString()} out
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Cost Today</CardTitle>
                        <DollarSign className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{todayCostDisplay}</div>
                        <p className="text-xs text-muted-foreground">Across all providers (24h)</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg Latency</CardTitle>
                        <Zap className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {isLoading ? "..." : `${stats?.avg_latency_ms ?? 0} ms`}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Error rate: {stats?.error_rate_percent ?? 0}%
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Token usage line chart */}
            <Card>
                <CardHeader>
                    <CardTitle>Token Usage — Last {hours}h</CardTitle>
                    <CardDescription>Hourly breakdown of prompt and completion tokens</CardDescription>
                </CardHeader>
                <CardContent className="pl-2">
                    <div className="h-[280px]">
                        {timelineLoading ? (
                            <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                                Loading chart…
                            </div>
                        ) : timeline.length === 0 ? (
                            <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                                No data for this period yet. Send a request to see usage here.
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={timeline} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-muted" />
                                    <XAxis
                                        dataKey="time"
                                        stroke="#888888"
                                        fontSize={11}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
                                        stroke="#888888"
                                        fontSize={11}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
                                        width={40}
                                    />
                                    <Tooltip
                                        formatter={(value: any, name?: string) => [
                                            Number(value).toLocaleString(),
                                            name === "prompt_tokens" ? "Prompt" : name === "completion_tokens" ? "Completion" : "Total"
                                        ]}
                                    />
                                    <Legend formatter={(v) => v === "prompt_tokens" ? "Prompt" : v === "completion_tokens" ? "Completion" : "Total"} />
                                    <Line type="monotone" dataKey="prompt_tokens" stroke="#3b82f6" strokeWidth={2} dot={false} />
                                    <Line type="monotone" dataKey="completion_tokens" stroke="#10b981" strokeWidth={2} dot={false} />
                                    <Line type="monotone" dataKey="total_tokens" stroke="#f59e0b" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                                </LineChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Cost by provider bar chart */}
            <Card>
                <CardHeader>
                    <CardTitle>Cost by Provider — Last 24h</CardTitle>
                    <CardDescription>Estimated spend in USD per provider</CardDescription>
                </CardHeader>
                <CardContent className="pl-2">
                    <div className="h-[220px]">
                        {usageLoading ? (
                            <div className="flex h-full items-center justify-center text-muted-foreground text-sm">Loading…</div>
                        ) : usage.length === 0 ? (
                            <div className="flex h-full items-center justify-center text-muted-foreground text-sm">No cost data yet.</div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={usage} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-muted" />
                                    <XAxis dataKey="provider" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                                    <YAxis stroke="#888888" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `$${v.toFixed(4)}`} width={60} />
                                    <Tooltip formatter={(v: any) => [`$${Number(v).toFixed(6)}`, "Cost (USD)"]} />
                                    <Bar dataKey="cost_usd" radius={[4, 4, 0, 0]}>
                                        {usage.map((entry: any) => (
                                            <rect key={entry.provider} fill={providerColor(entry.provider)} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
