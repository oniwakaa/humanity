"use client";

import * as React from "react";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { LikertScale } from "@/components/reflection/likert-scale";
import { OpenResponse } from "@/components/reflection/open-response";
import { cn } from "@/lib/utils";

interface Question {
    id: string;
    type: "likert" | "open";
    text: string;
    lowLabel?: string;
    highLabel?: string;
    placeholder?: string;
}

interface QuestionCardProps {
    question: Question;
    onAnswer: (value: number | string) => void;
    className?: string;
}

export function QuestionCard({ question, onAnswer, className }: QuestionCardProps) {
    const [likertValue, setLikertValue] = useState<number | null>(null);
    const [openValue, setOpenValue] = useState("");
    const [isRevealed, setIsRevealed] = useState(false);

    // Blur-text reveal effect
    useEffect(() => {
        const timer = setTimeout(() => setIsRevealed(true), 100);
        return () => clearTimeout(timer);
    }, [question.id]);

    const hasInput = question.type === "likert"
        ? likertValue !== null
        : openValue.trim().length > 0;

    const handleNext = () => {
        if (question.type === "likert" && likertValue !== null) {
            onAnswer(likertValue);
        } else if (question.type === "open" && openValue.trim()) {
            onAnswer(openValue.trim());
        }
    };

    // Split text for word-by-word animation
    const words = question.text.split(" ");

    return (
        <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -40 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className={cn(
                "flex flex-col items-center gap-12 w-full max-w-2xl mx-auto px-6",
                className
            )}
        >
            {/* Question text with blur reveal */}
            <h2 className="text-3xl md:text-4xl font-light text-white text-center leading-relaxed">
                {words.map((word, index) => (
                    <span
                        key={index}
                        className="inline-block transition-all duration-700"
                        style={{
                            transitionDelay: `${index * 60}ms`,
                            filter: isRevealed ? "blur(0px)" : "blur(12px)",
                            opacity: isRevealed ? 1 : 0,
                            transform: isRevealed ? "translateY(0)" : "translateY(20px)",
                            marginRight: "0.3em",
                        }}
                    >
                        {word}
                    </span>
                ))}
            </h2>

            {/* Input based on type */}
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.5, duration: 0.4 }}
                className="w-full flex justify-center"
            >
                {question.type === "likert" ? (
                    <LikertScale
                        value={likertValue}
                        onChange={setLikertValue}
                        lowLabel={question.lowLabel || "Not at all"}
                        highLabel={question.highLabel || "Completely"}
                    />
                ) : (
                    <OpenResponse
                        value={openValue}
                        onChange={setOpenValue}
                        placeholder={question.placeholder || "Share your thoughts..."}
                    />
                )}
            </motion.div>

            {/* Next button - appears after input */}
            <AnimatePresence>
                {hasInput && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 20 }}
                        transition={{ duration: 0.3 }}
                    >
                        <Button
                            size="lg"
                            onClick={handleNext}
                            className="rounded-full px-8 py-6 text-lg bg-white/10 backdrop-blur-sm border border-white/20 text-white hover:bg-white/20"
                        >
                            Continue
                        </Button>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
