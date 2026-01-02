"use client";

import * as React from "react";
import { useState, useEffect, useCallback } from "react";
import { Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Type declarations for Web Speech API
interface SpeechRecognitionResult {
    transcript: string;
    confidence: number;
}

interface SpeechRecognitionResultList {
    length: number;
    item(index: number): SpeechRecognitionResult[];
    [index: number]: SpeechRecognitionResult[];
}

interface SpeechRecognitionEventResult {
    results: SpeechRecognitionResultList;
}

interface VoiceInputButtonProps {
    onTranscript: (text: string) => void;
    disabled?: boolean;
    className?: string;
}

export function VoiceInputButton({
    onTranscript,
    disabled = false,
    className,
}: VoiceInputButtonProps) {
    const [isListening, setIsListening] = useState(false);
    const [isSupported, setIsSupported] = useState(false);

    useEffect(() => {
        // Check if Web Speech API is supported
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
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-US";

        recognition.onstart = () => {
            setIsListening(true);
        };

        recognition.onresult = (event: SpeechRecognitionEventResult) => {
            const transcript = event.results[0][0].transcript;
            onTranscript(transcript);
        };

        recognition.onerror = (event: { error: string }) => {
            console.error("Speech recognition error:", event.error);
            setIsListening(false);
        };

        recognition.onend = () => {
            setIsListening(false);
        };

        recognition.start();
    }, [isSupported, onTranscript]);

    if (!isSupported) {
        return null; // Don't render if not supported
    }

    return (
        <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={startListening}
            disabled={disabled || isListening}
            className={cn(
                "h-8 w-8 shrink-0",
                isListening && "text-destructive animate-pulse",
                className
            )}
            title={isListening ? "Listening..." : "Click to speak"}
        >
            {isListening ? (
                <MicOff className="h-4 w-4" />
            ) : (
                <Mic className="h-4 w-4" />
            )}
        </Button>
    );
}
