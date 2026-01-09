"use client";

import * as React from "react";
import { ArrowRight } from "lucide-react";
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
    const textareaRef = React.useRef<HTMLTextAreaElement>(null);

    const handleSubmit = () => {
        if (value.trim() && textareaRef.current) {
            onChange(value.trim());
            textareaRef.current.blur();
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className={cn("relative w-full max-w-lg", className)}>
            <div className="relative">
                <textarea
                    ref={textareaRef}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    rows={4}
                    className={cn(
                        "w-full px-4 py-3 rounded-xl resize-none pr-14",
                        "bg-white/10 backdrop-blur-sm border border-white/20",
                        "text-white placeholder:text-white/50",
                        "text-lg leading-relaxed",
                        "focus:outline-none focus:ring-2 focus:ring-white/30 focus:border-white/40",
                        "transition-all duration-300"
                    )}
                />
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={handleSubmit}
                    disabled={!value.trim()}
                    className={cn(
                        "absolute right-3 bottom-3",
                        "h-10 w-10 rounded-full",
                        "bg-white/10 hover:bg-white/20 text-white",
                        "!opacity-100",
                        !value.trim() && "opacity-50 cursor-not-allowed"
                    )}
                    title="Submit response"
                >
                    <ArrowRight className="h-5 w-5" />
                </Button>
            </div>
        </div>
    );
}
