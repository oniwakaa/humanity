'use client'
import React, { useState } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import { Server, MessageSquare, Database, Mic, ArrowRight } from 'lucide-react';
import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      className={cn(
        "file:text-foreground placeholder:text-muted-foreground selection:bg-primary selection:text-primary-foreground dark:bg-input/30 border-input flex h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]",
        "aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
        className
      )}
      {...props}
    />
  )
}

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
  // Defaults
  const [formData, setFormData] = useState<SetupData>({
    ollamaUrl: "http://127.0.0.1:11434",
    chatModel: "hf.co/unsloth/SmolLM3-3B-GGUF:Q4_K_M",
    embedModel: "mxbai-embed-large:latest",
    qdrantUrl: "http://127.0.0.1:6333",
    sttPath: "./models/ggml-base.en.bin",
  });

  const [isLoading, setIsLoading] = useState(false);
  const [focusedInput, setFocusedInput] = useState<string | null>(null);

  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  // For 3D card effect
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const rotateX = useTransform(mouseY, [-300, 300], [5, -5]);
  const rotateY = useTransform(mouseX, [-300, 300], [-5, 5]);

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = e.currentTarget.getBoundingClientRect();
    mouseX.set(e.clientX - rect.left - rect.width / 2);
    mouseY.set(e.clientY - rect.top - rect.height / 2);
    setMousePosition({ x: e.clientX, y: e.clientY });
  };

  const handleMouseLeave = () => {
    mouseX.set(0);
    mouseY.set(0);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    setIsLoading(true);
    // Simulate check or just proceed
    setTimeout(() => {
      setIsLoading(false);
      onComplete(formData);
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-md overflow-hidden">
      {/* Background gradients from original component */}
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
          {/* Glass card background */}
          <div className="relative bg-black/60 backdrop-blur-xl rounded-2xl p-8 border border-white/10 shadow-2xl overflow-hidden">

            {/* Header */}
            <div className="text-center space-y-2 mb-6">
              <motion.h1
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-white to-white/70"
              >
                Setup Wizard
              </motion.h1>
              <p className="text-white/60 text-sm">
                Configure your local AI environment.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Ollama URL */}
              <div className="space-y-1">
                <label className="text-xs text-white/70 ml-1">Ollama Base URL</label>
                <div className="relative flex items-center">
                  <Server className="absolute left-3 w-4 h-4 text-white/50" />
                  <Input
                    value={formData.ollamaUrl}
                    onChange={e => setFormData({ ...formData, ollamaUrl: e.target.value })}
                    onFocus={() => setFocusedInput('ollama')}
                    onBlur={() => setFocusedInput(null)}
                    className="pl-10 bg-white/5 border-white/10 text-white focus:bg-white/10"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs text-white/70 ml-1">Chat Model</label>
                  <div className="relative flex items-center">
                    <MessageSquare className="absolute left-3 w-4 h-4 text-white/50" />
                    <Input
                      value={formData.chatModel}
                      onChange={e => setFormData({ ...formData, chatModel: e.target.value })}
                      className="pl-10 bg-white/5 border-white/10 text-white focus:bg-white/10"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-white/70 ml-1">Embed Model</label>
                  <div className="relative flex items-center">
                    <MessageSquare className="absolute left-3 w-4 h-4 text-white/50" />
                    <Input
                      value={formData.embedModel}
                      onChange={e => setFormData({ ...formData, embedModel: e.target.value })}
                      className="pl-10 bg-white/5 border-white/10 text-white focus:bg-white/10"
                    />
                  </div>
                </div>
              </div>

              {/* Qdrant URL */}
              <div className="space-y-1">
                <label className="text-xs text-white/70 ml-1">Qdrant Base URL</label>
                <div className="relative flex items-center">
                  <Database className="absolute left-3 w-4 h-4 text-white/50" />
                  <Input
                    value={formData.qdrantUrl}
                    onChange={e => setFormData({ ...formData, qdrantUrl: e.target.value })}
                    className="pl-10 bg-white/5 border-white/10 text-white focus:bg-white/10"
                  />
                </div>
              </div>

              {/* STT Path */}
              <div className="space-y-1">
                <label className="text-xs text-white/70 ml-1">Whisper Model Path</label>
                <div className="relative flex items-center">
                  <Mic className="absolute left-3 w-4 h-4 text-white/50" />
                  <Input
                    value={formData.sttPath}
                    onChange={e => setFormData({ ...formData, sttPath: e.target.value })}
                    className="pl-10 bg-white/5 border-white/10 text-white focus:bg-white/10"
                  />
                </div>
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="submit"
                disabled={isLoading}
                className="w-full mt-6 bg-white text-black font-medium h-10 rounded-lg flex items-center justify-center relative overlow-hidden"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-black/70 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <span className="flex items-center gap-2">
                    Finish Setup <ArrowRight className="w-4 h-4" />
                  </span>
                )}
              </motion.button>
            </form>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
