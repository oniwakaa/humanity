"use client";

import { useEffect, useState } from "react";
import OnboardCard from "@/components/ui/onboard-card";
import { useTheme } from "next-themes";

declare global {
    interface Window {
        electron: any;
    }
}

export function SplashScreenComp() {
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState("Initializing...");
    const { setTheme } = useTheme();

    useEffect(() => {
        // Force dark mode for splash if desired, or respect system
        setTheme("dark");

        // Listen for IPC messages from Main Process
        if (typeof window !== "undefined" && window.electron && window.electron.ipcRenderer) {
            window.electron.ipcRenderer.on("init-status", (event: any, data: { status: string; progress: number }) => {
                // console.log("Splash received:", data);
                setStatus(data.status);
                setProgress(data.progress);
            });
        }

        // Fallback/Demo mode if not in Electron (for dev testing in browser)
        if (typeof window !== "undefined" && !window.electron) {
            const interval = setInterval(() => {
                setProgress((prev) => {
                    if (prev >= 100) {
                        clearInterval(interval);
                        return 100;
                    }
                    return prev + 1; // Slow increment
                });
            }, 100);
            return () => clearInterval(interval);
        }
    }, [setTheme]);

    return (
        <div className="flex items-center justify-center min-h-screen bg-black select-none">
            <OnboardCard
                progress={progress}
                step2={status} // reusing step2 for dynamic status
            />
        </div>
    );
}
