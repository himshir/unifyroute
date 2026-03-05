import { useState, useEffect } from "react"
import Editor from "@monaco-editor/react"
import yamlLib from "js-yaml"
import { useTheme } from "@/components/theme-provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Save } from "lucide-react"
import { useRoutingConfig, saveRoutingConfig } from "@/lib/api"
import { ErrorState } from "@/components/error-state"

export function RoutingConfig() {
    const { routingConfig, isLoading, isError, mutate } = useRoutingConfig()
    const [yaml, setYaml] = useState("")
    const [isSaving, setIsSaving] = useState(false)
    const { theme } = useTheme()
    const [parseError, setParseError] = useState<string | null>(null)
    const [parsedData, setParsedData] = useState<any>(null)

    useEffect(() => {
        if (routingConfig !== undefined) {
            setYaml(routingConfig)
        }
    }, [routingConfig])

    useEffect(() => {
        try {
            const data = yamlLib.load(yaml)
            setParsedData(data)
            setParseError(null)
        } catch (e: any) {
            setParseError(e.message)
        }
    }, [yaml])

    const handleSave = async () => {
        setIsSaving(true)
        try {
            await saveRoutingConfig(yaml)
            await mutate()
        } catch (e) {
            console.error(e)
            alert("Failed to save configuration")
        } finally {
            setIsSaving(false)
        }
    }

    if (isLoading) return <div className="p-8">Loading configuration...</div>
    if (isError) return <ErrorState />

    return (
        <div className="p-8 space-y-8 h-full flex flex-col">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Routing Configuration</h2>
                    <p className="text-muted-foreground pt-1">Define routing rules, model tiers, and failover strategies.</p>
                </div>
                <Button onClick={handleSave} disabled={isSaving}>
                    <Save className="mr-2 h-4 w-4" /> {isSaving ? "Saving..." : "Apply Changes"}
                </Button>
            </div>

            <Tabs defaultValue="editor" className="flex-1 flex flex-col">
                <TabsList className="w-[400px]">
                    <TabsTrigger value="editor" className="flex-1">YAML Editor</TabsTrigger>
                    <TabsTrigger value="visual" className="flex-1">Visual Editor</TabsTrigger>
                </TabsList>
                <TabsContent value="editor" className="flex-1 mt-6">
                    <Card className="h-full flex flex-col border-slate-200 shadow-sm">
                        <CardHeader className="pb-3 border-b bg-slate-50/50">
                            <CardTitle className="text-sm font-medium">routing.yaml</CardTitle>
                            <CardDescription>Changes apply instantly to the router without restart.</CardDescription>
                        </CardHeader>
                        <CardContent className="p-0 flex-1 relative">
                            <Editor
                                height="100%"
                                defaultLanguage="yaml"
                                theme={theme === "dark" ? "vs-dark" : "light"}
                                value={yaml}
                                onChange={(val) => setYaml(val || "")}
                                options={{
                                    minimap: { enabled: false },
                                    fontSize: 14,
                                    wordWrap: "on",
                                    scrollBeyondLastLine: false,
                                }}
                            />
                            {parseError && (
                                <div className="absolute bottom-0 left-0 right-0 bg-destructive/90 text-destructive-foreground p-2 text-xs font-mono">
                                    YAML Parse Error: {parseError}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
                <TabsContent value="visual">
                    <Card>
                        <CardContent className="h-[600px] overflow-auto p-6">
                            {parseError ? (
                                <div className="text-destructive flex items-center justify-center h-full">
                                    Cannot use visual editor while YAML has syntax errors. Please fix them in the YAML Editor tab.
                                </div>
                            ) : !parsedData?.tiers ? (
                                <div className="text-muted-foreground flex items-center justify-center h-full">
                                    No tiers found in configuration.
                                </div>
                            ) : (
                                <div className="space-y-6">
                                    {Object.entries(parsedData.tiers).map(([tierName, models]: [string, any]) => (
                                        <Card key={tierName} className="border-slate-200 shadow-sm overflow-hidden">
                                            <div className="bg-slate-100 dark:bg-slate-800/50 px-4 py-2 border-b font-semibold text-sm">
                                                Tier: {tierName}
                                            </div>
                                            <ul className="divide-y">
                                                {Array.isArray(models) && models.map((modelId: string, idx: number) => (
                                                    <li key={`${tierName}-${idx}`} className="px-4 py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-900/50 group">
                                                        <span className="font-mono text-sm">{modelId}</span>
                                                        <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity">
                                                            <Button
                                                                variant="outline" size="sm" className="h-7 w-7 p-0"
                                                                disabled={idx === 0}
                                                                onClick={() => {
                                                                    const newModels = [...models]
                                                                    const tmp = newModels[idx - 1]
                                                                    newModels[idx - 1] = newModels[idx]
                                                                    newModels[idx] = tmp
                                                                    const newData = { ...parsedData, tiers: { ...parsedData.tiers, [tierName]: newModels } }
                                                                    setYaml(yamlLib.dump(newData))
                                                                }}
                                                            >↑</Button>
                                                            <Button
                                                                variant="outline" size="sm" className="h-7 w-7 p-0"
                                                                disabled={idx === models.length - 1}
                                                                onClick={() => {
                                                                    const newModels = [...models]
                                                                    const tmp = newModels[idx + 1]
                                                                    newModels[idx + 1] = newModels[idx]
                                                                    newModels[idx] = tmp
                                                                    const newData = { ...parsedData, tiers: { ...parsedData.tiers, [tierName]: newModels } }
                                                                    setYaml(yamlLib.dump(newData))
                                                                }}
                                                            >↓</Button>
                                                        </div>
                                                    </li>
                                                ))}
                                                {(!Array.isArray(models) || models.length === 0) && (
                                                    <li className="px-4 py-3 text-sm text-muted-foreground italic">No models in this tier.</li>
                                                )}
                                            </ul>
                                        </Card>
                                    ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    )
}
