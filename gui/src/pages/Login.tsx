import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Lock, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { setAuthToken } from "@/lib/api";

export function Login() {
    const [credential, setCredential] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const navigate = useNavigate();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!credential.trim()) {
            setError("Please enter your master password or admin key");
            return;
        }

        setLoading(true);
        setError("");

        try {
            // Try password authentication first
            try {
                const loginRes = await fetch("/api/admin/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    credentials: "include",
                    body: JSON.stringify({ password: credential })
                });

                if (loginRes.ok) {
                    // Password login successful
                    const data = await loginRes.json();
                    setAuthToken(data.token);
                    navigate("/wizard");
                    return;
                }
            } catch (passwordErr) {
                // Password attempt failed, will try API key next
            }

            // Try API key authentication
            try {
                const testRes = await fetch("/api/admin/providers", {
                    method: "GET",
                    headers: {
                        "Authorization": `Bearer ${credential}`
                    },
                    credentials: "include"
                });

                if (testRes.ok) {
                    // API key is valid, store it as the token
                    setAuthToken(credential);
                    navigate("/wizard");
                    return;
                }
            } catch (keyErr) {
                // API key attempt failed
            }

            // Both authentication methods failed
            setError("Invalid master password or API key. Please try again.");
            setLoading(false);
        } catch (err: any) {
            setError(err.message || "Authentication failed. Please try again.");
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
            <div className="w-full max-w-sm space-y-8">
                {/* Logo & Headline */}
                <div className="flex flex-col items-center">
                    <div className="w-16 h-16 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm flex items-center justify-center mb-6">
                        <img src="/images/favicon.png" alt="UnifyRoute Logo" className="w-10 h-10 object-contain" />
                    </div>
                    <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                        <span className="text-orange-600">Unify</span><span className="text-slate-900 dark:text-slate-100">Route</span>
                    </h2>
                    <p className="text-sm text-slate-500 mt-2 font-medium tracking-wide">Admin Login</p>
                </div>

                {/* Login Form Card */}
                <div className="bg-white dark:bg-slate-950 p-8 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                    <form onSubmit={handleLogin} className="space-y-5">
                        <div className="space-y-2">
                            <Label htmlFor="credential" className="text-xs text-slate-500 font-bold tracking-wider">
                                Master Password or Admin Key
                            </Label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Lock className="h-4 w-4 text-slate-400" />
                                </div>
                                <Input
                                    id="credential"
                                    type="password"
                                    placeholder="Enter your master password or API key"
                                    autoComplete="current-password"
                                    className="pl-10 h-12 bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 focus-visible:ring-orange-500"
                                    value={credential}
                                    onChange={(e) => setCredential(e.target.value)}
                                    disabled={loading}
                                />
                            </div>
                        </div>

                        {error && (
                            <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg flex items-start gap-2">
                                <Lock className="h-4 w-4 mt-0.5 shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}

                        <Button
                            type="submit"
                            className="w-full h-12 font-semibold text-white bg-orange-600 hover:bg-orange-700 transition-colors shadow-none"
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Authenticating...
                                </>
                            ) : (
                                "Sign In"
                            )}
                        </Button>
                    </form>
                </div>

                <div className="text-center">
                    <p className="text-xs text-slate-400 font-medium tracking-wide">
                        &copy; {new Date().getFullYear()} UnifyRoute. All rights reserved.
                    </p>
                </div>
            </div>
        </div>
    );
}
