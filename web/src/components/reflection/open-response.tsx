"use client";

import * as React from "react";
import { useState, useCallback } from "react";
import { Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface OpenResponseProps {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    className?: string;
}

export function OpenResponse({
    value,
    onChange,
    placeholder = "Share your thoughts...",
    className,
}: OpenResponseProps) {
    const [isListening, setIsListening] = useState(false);
    const [isSupported, setIsSupported] = useState(false);
    const [interimTranscript, setInterimTranscript] = useState("");

    // Ref to track if we *should* be listening, to handle auto-stops
    const shouldListenRef = React.useRef(false);
    // Ref to keep the latest value accessible inside callbacks without dependency loops
    const valueRef = React.useRef(value);

    React.useEffect(() => {
        valueRef.current = value;
    }, [value]);

    React.useEffect(() => {
        setIsSupported(
            typeof window !== "undefined" &&
            ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)
        );
    }, []);

    const startListening = useCallback(() => {
        if (!isSupported || typeof window === "undefined") return;

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (!SpeechRecognitionAPI) return;

        const recognition = new SpeechRecognitionAPI();
        recognition.continuous = true; // Enable continuous recording
        recognition.interimResults = true; // Show results while likely still speaking
        recognition.lang = "en-US";

        recognition.onstart = () => {
            setIsListening(true);
            shouldListenRef.current = true;
        };

        recognition.onresult = (event: any) => {
            let finalTranscript = "";
            let currentInterim = "";

            for (let i = event.resultIndex; i < (event.results as any).length; ++i) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + " ";
                } else {
                    currentInterim += transcript;
                }
            }

            if (finalTranscript) {
                // intelligently append to existing value
                const prev = valueRef.current || "";
                // Add space if needed
                const spacer = prev && !prev.endsWith(" ") ? " " : "";
                onChange(prev + spacer + finalTranscript.trim());
            }

            setInterimTranscript(currentInterim);
        };

        recognition.onerror = (event: { error: string }) => {
            console.error("Speech recognition error:", event.error);
            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                shouldListenRef.current = false;
                setIsListening(false);
            }
            // For other errors like 'no-speech', we might want to just let it restart via onend
        };

        recognition.onend = () => {
            // content ended, flush interim if any (though usually empty on end)
            setInterimTranscript("");

            // Auto-restart if we didn't intend to stop
            if (shouldListenRef.current) {
                try {
                    recognition.start();
                } catch (e) {
                    console.error("Failed to restart recognition:", e);
                    setIsListening(false);
                    shouldListenRef.current = false;
                }
            } else {
                setIsListening(false);
            }
        };

        try {
            recognition.start();
        } catch (e) {
            console.error("Failed to start recognition:", e);
            setIsListening(false);
        }
    }, [isSupported, onChange]);

    const stopListening = useCallback(() => {
        shouldListenRef.current = false;
        // reliance on existing recognition instance to stop via its onend or auto-timeout
        // triggering a "stop" on the window explicitly isn't clean since we don't store the instance in a ref
        // but setting shouldListenRef to false ensures it won't restart.
        // To force stop effectively, we can reload the page or just accept it will die out.
        // Ideally we store recognition in a ref to call .stop(), let's improving that.

        // Since we didn't store the recognition instance in a ref in the previous simplified version, 
        // we can't call .stop() on it directly here easily without refactoring to a class or using a ref for the instance.
        // HACK: For this 'function-scope' approach, we rely on the `voice` UI toggle.
        // However, to be robust, let's fix the implementation to store the instance.
        setIsListening(false);
        // The recognition.onend will fire eventually or we can force it if we had the instance. 
        // With the current refactor below, we will use a ref for the recognition object.
    }, []);

    // Better implementation using a ref for the recognition instance
    const recognitionRef = React.useRef<any>(null);

    const toggleListening = useCallback(() => {
        if (isListening) {
            // Stop
            shouldListenRef.current = false;
            if (recognitionRef.current) {
                recognitionRef.current.stop();
            }
            setIsListening(false);
        } else {
            // Start
            if (!isSupported || typeof window === "undefined") return;

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const SpeechRecognitionAPI = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
            if (!SpeechRecognitionAPI) return;

            const recognition = new SpeechRecognitionAPI();
            recognitionRef.current = recognition;

            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = "en-US";

            recognition.onstart = () => {
                setIsListening(true);
                shouldListenRef.current = true;
            };

            recognition.onresult = (event: any) => {
                let incrementalFinal = "";
                let currentInterim = "";

                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        incrementalFinal += transcript + " ";
                    } else {
                        currentInterim += transcript;
                    }
                }

                if (incrementalFinal) {
                    // update the main value
                    const prev = valueRef.current || "";
                    const spacer = prev && !prev.endsWith(" ") ? " " : "";
                    onChange(prev + spacer + incrementalFinal.trim());
                }
                setInterimTranscript(currentInterim);
            };

            recognition.onerror = (event: any) => {
                console.warn("Speech recognition error:", event.error);
                if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                    shouldListenRef.current = false;
                    setIsListening(false);
                }
            };

            recognition.onend = () => {
                setInterimTranscript("");
                if (shouldListenRef.current) {
                    // unexpected end, restart
                    try {
                        recognition.start();
                    } catch (e) {
                        // ignore error if already started
                    }
                } else {
                    setIsListening(false);
                }
            };

            try {
                recognition.start();
            } catch (e) {
                console.error("Failed to start:", e);
            }
        }
    }, [isSupported, isListening, onChange]);

    return (
        <div className={cn("relative w-full max-w-lg", className)}>
            <div className="relative">
                <textarea
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder={placeholder}
                    rows={4}
                    className={cn(
                        "w-full px-4 py-3 rounded-xl resize-none",
                        "bg-white/10 backdrop-blur-sm border border-white/20",
                        "text-white placeholder:text-white/50",
                        "text-lg leading-relaxed",
                        "focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-white/40",
                        "transition-all duration-300"
                    )}
                />
                {interimTranscript && (
                    <div className="absolute bottom-4 left-4 right-12 text-white/50 text-sm truncate pointer-events-none animate-pulse">
                        {interimTranscript}
                    </div>
                )}
            </div>

            {isSupported && (
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={toggleListening}
                    className={cn(
                        "absolute right-3 bottom-3",
                        "h-10 w-10 rounded-full",
                        "bg-white/10 hover:bg-white/20 text-white",
                        isListening && "text-red-400 animate-pulse bg-red-500/20"
                    )}
                    title={isListening ? "Stop listening" : "Start recording"}
                >
                    {isListening ? (
                        <MicOff className="h-5 w-5" />
                    ) : (
                        <Mic className="h-5 w-5" />
                    )}
                </Button>
            )}
        </div>
    );
}
