'use client'
import React, { useState } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import { Server, Database, ArrowRight } from 'lucide-react';
import { cn } from "@/lib/utils"

interface SetupData {
  ollamaUrl: string;
  chatModel: string;
  embedModel: string;
  qdrantUrl: string;
  sttPath: string;
}



interface SetupModalProps {
  onComplete: (data: SetupData) => void;
}

export default function SetupModal({ onComplete }: SetupModalProps) {
  const [modelStatuses, setModelStatuses] = useState<any[]>([]);
  const [isOllamaRunning, setIsOllamaRunning] = useState(false);
  const [polling, setPolling] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  // 3D card effect state
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const rotateX = useTransform(mouseY, [-300, 300], [5, -5]);
  const rotateY = useTransform(mouseX, [-300, 300], [-5, 5]);

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    mouseX.set(e.clientX - rect.left - rect.width / 2);
    mouseY.set(e.clientY - rect.top - rect.height / 2);
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  // Poll status
  React.useEffect(() => {
    if (!polling) return;

    const interval = setInterval(async () => {
      try {
        const API_BASE = "http://127.0.0.1:8000"; // Assuming local backend
        const res = await fetch(`${API_BASE}/api/models`);

        if (!res.ok) throw new Error("Backend unreachable");

        const data = await res.json();
        setModelStatuses(data);

        // check if ollama is reachable (data is array, not error dict)
        // If data is array of status objects, check if any has status 'error' AND detail implies connection fail?
        // Actually server returns "status": "error" if ollama unreachable.
        const ollamaError = data.find((m: any) => m.status === 'error' && m.detail?.includes("connect"));
        setIsOllamaRunning(!ollamaError);

        // Auto-trigger downloads if missing
        if (!ollamaError) {
          data.forEach(async (m: any) => {
            if (m.status === 'missing') {
              try {
                await fetch(`${API_BASE}/api/models/pull`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ name: m.name })
                });
              } catch (e) { console.error("Auto-pull failed", e); }
            }
          });
        }

      } catch (e) {
        console.warn("Polling error:", e);
        setIsOllamaRunning(false);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [polling]);

  const allReady = modelStatuses.length > 0 && modelStatuses.every((m: any) => m.status === 'ready');

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!allReady) return;

    setIsLoading(true);
    // Hardcoded defaults for Zero-Config
    const configData: SetupData = {
      ollamaUrl: "http://127.0.0.1:11434",
      chatModel: "hf.co/unsloth/SmolLM3-3B-GGUF:Q4_K_M",
      embedModel: "mxbai-embed-large:latest",
      qdrantUrl: "http://127.0.0.1:6333", // Legacy field, kept for type compatibility
      sttPath: "./models/ggml-base.en.bin",
    };

    setTimeout(() => {
      setIsLoading(false);
      onComplete(configData);
    }, 500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-md overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-purple-900/20 via-black/50 to-black/80 pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-lg relative z-10 p-4"
        style={{ perspective: 1500 }}
      >
        <motion.div
          className="relative"
          style={{ rotateX, rotateY }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <div className="relative bg-black/60 backdrop-blur-xl rounded-2xl p-8 border border-white/10 shadow-2xl overflow-hidden min-h-[400px] flex flex-col">

            <div className="text-center space-y-2 mb-8">
              <motion.h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-white to-white/70">
                System Check
              </motion.h1>
              <p className="text-white/60 text-sm">
                Verifying local AI components...
              </p>
            </div>

            <div className="flex-1 space-y-6">
              {/* Ollama Status */}
              <div className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="flex items-center gap-3">
                  <Server className={cn("w-5 h-5", isOllamaRunning ? "text-emerald-400" : "text-red-400")} />
                  <div>
                    <div className="text-sm font-medium text-white">Local AI Service</div>
                    <div className="text-xs text-white/50">{isOllamaRunning ? "Running (Ollama)" : "Not Detected"}</div>
                  </div>
                </div>
                <div className={cn("px-2 py-1 rounded text-xs font-medium", isOllamaRunning ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/20 text-red-300")}>
                  {isOllamaRunning ? "Online" : "Offline"}
                </div>
              </div>

              {!isOllamaRunning && (
                <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-xs text-yellow-200/80">
                  Please ensure <strong>Ollama</strong> is installed and running on your system.
                  <br /><a href="https://ollama.com" target="_blank" className="underline hover:text-white mt-1 inline-block">Download Ollama</a>
                </div>
              )}

              {/* Models Status */}
              {isOllamaRunning && (
                <div className="space-y-3">
                  <h3 className="text-xs font-medium text-white/40 uppercase tracking-wider ml-1">Required Models</h3>
                  {modelStatuses.map((model, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-white/5 border border-white/10 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Database className="w-4 h-4 text-purple-400" />
                          <span className="text-sm text-white/90 truncate max-w-[200px]" title={model.name}>
                            {model.name.split('/').pop()?.split(':')[0]}
                          </span>
                        </div>
                        <span className={cn("text-xs capitalize",
                          model.status === 'ready' ? "text-emerald-400" : "text-blue-400"
                        )}>
                          {model.status === 'ready' ? "Ready" : model.status} {model.status === 'downloading' && `(${Math.round(model.progress)}%)`}
                        </span>
                      </div>
                      {model.status === 'downloading' && (
                        <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
                          <motion.div
                            className="h-full bg-blue-500"
                            initial={{ width: 0 }}
                            animate={{ width: `${model.progress}%` }}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleSubmit}
              disabled={!allReady || isLoading}
              className={cn(
                "w-full mt-6 font-medium h-12 rounded-xl flex items-center justify-center relative overflow-hidden transition-all",
                allReady
                  ? "bg-white text-black hover:bg-white/90 shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                  : "bg-white/10 text-white/30 cursor-not-allowed"
              )}
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-black/70 border-t-transparent rounded-full animate-spin" />
              ) : (
                <span className="flex items-center gap-2">
                  Launch Application <ArrowRight className="w-4 h-4" />
                </span>
              )}
            </motion.button>

          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
