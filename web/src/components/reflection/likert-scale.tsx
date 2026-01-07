"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface LikertScaleProps {
    value: number | null;
    onChange: (value: number) => void;
    min?: number;
    max?: number;
    lowLabel?: string;
    highLabel?: string;
    className?: string;
}

export function LikertScale({
    value,
    onChange,
    min = 1,
    max = 7,
    lowLabel = "Strongly Disagree",
    highLabel = "Strongly Agree",
    className,
}: LikertScaleProps) {
    const options = Array.from({ length: max - min + 1 }, (_, i) => min + i);

    return (
        <div className={cn("flex flex-col items-center gap-6", className)}>
            {/* Scale dots */}
            <div className="flex items-center gap-3">
                {options.map((option) => {
                    const isSelected = value === option;
                    const size = option === Math.ceil((min + max) / 2) ? "w-6 h-6" : "w-5 h-5";

                    return (
                        <button
                            key={option}
                            type="button"
                            onClick={() => onChange(option)}
                            className={cn(
                                size,
                                "rounded-full transition-all duration-300 ease-out",
                                "border-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-white/50",
                                "hover:scale-125 hover:border-white",
                                isSelected
                                    ? "bg-white border-white shadow-[0_0_20px_rgba(255,255,255,0.5)]"
                                    : "bg-transparent border-white/40 hover:bg-white/20"
                            )}
                            aria-label={`Rate ${option} out of ${max}`}
                            aria-pressed={isSelected}
                        />
                    );
                })}
            </div>

            {/* Labels */}
            <div className="flex justify-between w-full max-w-md text-sm text-white/70">
                <span>{lowLabel}</span>
                <span>{highLabel}</span>
            </div>
        </div>
    );
}
