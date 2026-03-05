import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
    RadialBarChart, RadialBar, ResponsiveContainer,
    BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell
} from "recharts"
import { useUsageStats, useCredentials, useUsageDetails } from "@/lib/api"
import { Activity, DollarSign, Database, RefreshCw, ChevronDown, ChevronRight } from "lucide-react"
import { ErrorState } from "@/components/error-state"
import { Button } from "@/components/ui/button"


function QuotaGauge({ label, used, total, color }: { label: string; used: number; total: number; color: string }) {
    const pct = total > 0 ? Math.min(100, Math.round((used / total) * 100)) : 0
    const data = [{ name: label, value: pct, fill: pct > 80 ? "#ef4444" : pct > 60 ? "#f59e0b" : color }]

    return (
        <div className="flex flex-col items-center gap-1">
            <div className="h-[120px] w-[120px]">
                <ResponsiveContainer width="100%" height="100%">
                    <RadialBarChart
                        cx="50%"
                        cy="50%"
                        innerRadius="60%"
                        outerRadius="100%"
                        barSize={10}
                        data={data}
                        startAngle={90}
                        endAngle={-270}
                    >
                        <RadialBar background dataKey="value" cornerRadius={5} />
                    </RadialBarChart>
                </ResponsiveContainer>
            </div>
            <div className="text-center">
                <div className="text-lg font-bold">{pct}%</div>
                <div className="text-xs text-muted-foreground truncate max-w-[120px]" title={label}>{label}</div>
            </div>
        </div>
    )
}


function UsageDrilldown({ provider, days }: { provider: string; days: number }) {
    const { details, isLoading } = useUsageDetails(days, provider)

    if (isLoading) {
        return (
            <TableRow>
                <TableCell colSpan={6} className="py-3 pl-10 text-xs text-muted-foreground">Loading details…</TableCell>
            </TableRow>
        )
    }

    if (details.length === 0) {
        return (
            <TableRow>
                <TableCell colSpan={6} className="py-3 pl-10 text-xs text-muted-foreground">No per-credential data yet.</TableCell>
            </TableRow>
        )
    }

    // Group by credential
    const byCredential: Record<string, { label: string; models: typeof details; totals: { reqs: number; pt: number; ct: number; cost: number } }> = {}
    for (const d of details) {
        const key = d.credential_id || "unknown"
        if (!byCredential[key]) {
            byCredential[key] = { label: d.credential_label, models: [], totals: { reqs: 0, pt: 0, ct: 0, cost: 0 } }
        }
        byCredential[key].models.push(d)
        byCredential[key].totals.reqs += d.request_count
        byCredential[key].totals.pt += d.prompt_tokens
        byCredential[key].totals.ct += d.completion_tokens
        byCredential[key].totals.cost += d.cost_usd
    }

    return (
        <>
            {Object.entries(byCredential).map(([credId, cred]) => (
                <CredentialDrilldown key={credId} credId={credId} cred={cred} />
            ))}
        </>
    )
}


function CredentialDrilldown({ credId, cred }: {
    credId: string;
    cred: { label: string; models: any[]; totals: { reqs: number; pt: number; ct: number; cost: number } }
}) {
    const [expanded, setExpanded] = useState(false)

    return (
        <>
            <TableRow
                className="bg-muted/30 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => setExpanded(!expanded)}
            >
                <TableCell className="pl-10 text-xs">
                    <span className="inline-flex items-center gap-1">
                        {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                        <span className="font-medium">{cred.label}</span>
                        <span className="text-muted-foreground">({credId.slice(0, 8)}…)</span>
                    </span>
                </TableCell>
                <TableCell className="text-right font-mono text-xs">{cred.totals.reqs.toLocaleString()}</TableCell>
                <TableCell className="text-right font-mono text-xs text-muted-foreground">{cred.totals.pt.toLocaleString()}</TableCell>
                <TableCell className="text-right font-mono text-xs text-muted-foreground">{cred.totals.ct.toLocaleString()}</TableCell>
                <TableCell className="text-right font-mono text-xs">{(cred.totals.pt + cred.totals.ct).toLocaleString()}</TableCell>
                <TableCell className="text-right font-mono text-xs text-green-600">${cred.totals.cost.toFixed(4)}</TableCell>
            </TableRow>
            {expanded && cred.models.map((m: any, i: number) => (
                <TableRow key={i} className="bg-muted/10">
                    <TableCell className="pl-16 text-xs text-muted-foreground font-mono">{m.actual_model}</TableCell>
                    <TableCell className="text-right font-mono text-xs text-muted-foreground">{m.request_count.toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono text-xs text-muted-foreground">{m.prompt_tokens.toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono text-xs text-muted-foreground">{m.completion_tokens.toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono text-xs text-muted-foreground">{m.total_tokens.toLocaleString()}</TableCell>
                    <TableCell className="text-right font-mono text-xs text-muted-foreground">${Number(m.cost_usd).toFixed(4)}</TableCell>
                </TableRow>
            ))}
        </>
    )
}


export function Quota() {
    const [days, setDays] = useState(30)
    const [expandedProvider, setExpandedProvider] = useState<string | null>(null)
    const { usage, totalCost, totalRequests, isLoading, isError, mutate } = useUsageStats(days)
    const { credentials } = useCredentials()

    // Auto-refresh every 30 seconds
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
    useEffect(() => {
        intervalRef.current = setInterval(() => mutate(), 30000)
        return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
    }, [mutate])

    if (isError) return <ErrorState />

    // Build gauge data from credentials with expires_at
    const oauthCreds = Array.isArray(credentials)
        ? credentials.filter((c: any) => c.auth_type === "oauth2" && c.expires_at)
        : []

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Usage & Quota</h2>
                    <p className="text-muted-foreground pt-1">Token usage, estimated costs, and credential health.</p>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">Timeframe:</span>
                    <Select value={days.toString()} onValueChange={v => setDays(Number(v))}>
                        <SelectTrigger className="w-[140px]">
                            <SelectValue placeholder="Last 30 Days" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="1">Last 24 Hours</SelectItem>
                            <SelectItem value="7">Last 7 Days</SelectItem>
                            <SelectItem value="30">Last 30 Days</SelectItem>
                        </SelectContent>
                    </Select>
                    <Button variant="outline" size="sm" onClick={() => mutate()}>
                        <RefreshCw className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {/* Summary cards */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
                        <DollarSign className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{isLoading ? "..." : `$${totalCost.toFixed(4)}`}</div>
                        <p className="text-xs text-muted-foreground">Estimated from model pricing</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{isLoading ? "..." : totalRequests.toLocaleString()}</div>
                        <p className="text-xs text-muted-foreground">Successful completions</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Active Providers</CardTitle>
                        <Database className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{isLoading ? "..." : usage.length}</div>
                        <p className="text-xs text-muted-foreground">With traffic in this period</p>
                    </CardContent>
                </Card>
            </div>

            {/* OAuth credential health gauges */}
            {oauthCreds.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>OAuth Token Health</CardTitle>
                        <CardDescription>Time remaining before token expiry (auto-refreshes every 30s)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-6 justify-start">
                            {oauthCreds.map((c: any) => {
                                const expiresAt = new Date(c.expires_at)
                                const totalLifetime = 3600
                                const remaining = Math.max(0, (expiresAt.getTime() - Date.now()) / 1000)
                                return (
                                    <QuotaGauge
                                        key={c.id}
                                        label={c.label || "OAuth Credential"}
                                        used={totalLifetime - remaining}
                                        total={totalLifetime}
                                        color="#10b981"
                                    />
                                )
                            })}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Cost bar chart */}
            {usage.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Cost by Provider</CardTitle>
                        <CardDescription>Estimated USD spend per provider in the selected period</CardDescription>
                    </CardHeader>
                    <CardContent className="pl-2">
                        <div className="h-[200px]">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={usage} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="provider" fontSize={11} tickLine={false} axisLine={false} />
                                    <YAxis fontSize={11} tickLine={false} axisLine={false} tickFormatter={v => `$${Number(v).toFixed(4)}`} width={65} />
                                    <Tooltip formatter={(v: any) => [`$${Number(v).toFixed(6)}`, "Cost"]} />
                                    <Bar dataKey="cost_usd" radius={[4, 4, 0, 0]}>
                                        {usage.map((_: any, i: number) => (
                                            <Cell key={i} fill={["#3b82f6", "#10b981", "#f59e0b", "#a855f7", "#ec4899", "#14b8a6"][i % 6]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Provider breakdown table with drilldown */}
            <Card>
                <CardHeader>
                    <CardTitle>Usage Drilldown</CardTitle>
                    <CardDescription>Click a provider to see per-credential and per-model breakdown.</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="rounded-md border">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Provider / Credential / Model</TableHead>
                                    <TableHead className="text-right">Requests</TableHead>
                                    <TableHead className="text-right">Prompt Tokens</TableHead>
                                    <TableHead className="text-right">Completion Tokens</TableHead>
                                    <TableHead className="text-right">Total Tokens</TableHead>
                                    <TableHead className="text-right">Est. Cost</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {isLoading ? (
                                    <TableRow><TableCell colSpan={6} className="text-center py-8">Loading usage data...</TableCell></TableRow>
                                ) : usage.length === 0 ? (
                                    <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-8">No usage data. Make some requests first.</TableCell></TableRow>
                                ) : usage.map((row: any) => (
                                    <ProviderRow
                                        key={row.provider}
                                        row={row}
                                        days={days}
                                        expanded={expandedProvider === row.provider}
                                        onToggle={() => setExpandedProvider(expandedProvider === row.provider ? null : row.provider)}
                                    />
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}


function ProviderRow({ row, days, expanded, onToggle }: { row: any; days: number; expanded: boolean; onToggle: () => void }) {
    return (
        <>
            <TableRow
                className="cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={onToggle}
            >
                <TableCell className="font-medium">
                    <span className="inline-flex items-center gap-1.5">
                        {expanded
                            ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            : <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        }
                        {row.provider}
                    </span>
                </TableCell>
                <TableCell className="text-right font-mono text-sm">{row.request_count.toLocaleString()}</TableCell>
                <TableCell className="text-right font-mono text-sm text-muted-foreground">{row.prompt_tokens.toLocaleString()}</TableCell>
                <TableCell className="text-right font-mono text-sm text-muted-foreground">{row.completion_tokens.toLocaleString()}</TableCell>
                <TableCell className="text-right font-mono text-sm font-semibold">{row.total_tokens.toLocaleString()}</TableCell>
                <TableCell className="text-right font-mono text-sm text-green-600">${Number(row.cost_usd).toFixed(4)}</TableCell>
            </TableRow>
            {expanded && <UsageDrilldown provider={row.provider} days={days} />}
        </>
    )
}
