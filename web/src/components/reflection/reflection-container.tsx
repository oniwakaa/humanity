"use client";

import * as React from "react";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Component as EtheralShadow } from "@/components/ui/etheral-shadow";
import { QuestionCard } from "@/components/reflection/question-card";

// Define reflection questions
const QUESTIONS = [
    {
        id: "feeling",
        type: "likert" as const,
        text: "How are you feeling right now?",
        lowLabel: "Very low",
        highLabel: "Wonderful",
    },
    {
        id: "presence",
        type: "likert" as const,
        text: "How present were you today?",
        lowLabel: "Distracted",
        highLabel: "Fully present",
    },
    {
        id: "gratitude",
        type: "open" as const,
        text: "What's one thing you're grateful for today?",
        placeholder: "I'm grateful for...",
    },
    {
        id: "release",
        type: "open" as const,
        text: "What would you like to let go of?",
        placeholder: "I want to release...",
    },
];

type Step = "start" | number | "complete";

interface Answers {
    [key: string]: number | string;
}

export function ReflectionContainer() {
    const router = useRouter();
    const [step, setStep] = useState<Step>("start");
    const [answers, setAnswers] = useState<Answers>({});

    // Dynamic Questions State
    const [questions, setQuestions] = useState<any[]>(QUESTIONS);
    const [loading, setLoading] = useState(false);

    // Fetch questions on mount (or on start)
    const fetchQuestions = useCallback(async () => {
        setLoading(true);
        try {
            const { api } = await import("@/lib/api");
            // Check for locally saved questions or generate
            const data = await api.generateQuestions();
            if (data && data.questions && Array.isArray(data.questions)) {
                setQuestions(data.questions);
            }
        } catch (e) {
            console.error("Failed to load questions:", e);
            // Fallback to static is automatic since we init with QUESTIONS
        } finally {
            setLoading(false);
        }
    }, []);

    const handleStart = useCallback(() => {
        // Trigger fetch if we haven't already, or just start
        // For smoother UX, maybe we fetch on 'Start' click?
        fetchQuestions().then(() => {
            setStep(0);
        });
    }, [fetchQuestions]);

    const handleAnswer = useCallback((value: number | string) => {
        if (typeof step === "number") {
            const question = questions[step];
            setAnswers((prev) => ({ ...prev, [question.id]: value }));

            if (step < questions.length - 1) {
                setStep(step + 1);
            } else {
                setStep("complete");

                // Save to backend
                const cycleId = new Date().toISOString().split('T')[0]; // Simple Daily ID
                const answerList = Object.entries(answers).map(([qid, val]) => ({
                    question_id: qid,
                    value: val
                }));
                // Add current question answer
                answerList.push({ question_id: question.id, value: value });

                import("@/lib/api").then(({ api }) => {
                    api.submitDaily(cycleId, answerList).catch(err => console.error(err));
                });
                console.log("Reflection completed & submitting...");
            }
        }
    }, [step, answers]);

    const handleBack = useCallback(() => {
        router.push("/app");
    }, [router]);

    const currentQuestion = typeof step === "number" ? questions[step] : null;

    return (
        <div className="relative min-h-screen w-full overflow-hidden">
            {/* Ethereal background */}
            <div className="absolute inset-0 z-0">
                <EtheralShadow
                    color="rgba(50, 80, 140, 0.8)"
                    animation={{ scale: 30, speed: 15 }}
                    noise={{ opacity: 0.3, scale: 1 }}
                />
            </div>

            {/* Back button */}
            <Button
                variant="ghost"
                size="sm"
                onClick={handleBack}
                className="absolute top-6 left-6 z-20 text-white/70 hover:text-white hover:bg-white/10"
            >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
            </Button>

            {/* Content */}
            <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4">
                <AnimatePresence mode="wait">
                    {/* Start Screen */}
                    {step === "start" && (
                        <motion.div
                            key="start"
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.8 }}
                            transition={{ duration: 0.4 }}
                            className="flex flex-col items-center gap-8 text-center"
                        >
                            <h1 className="text-4xl md:text-5xl font-light text-white">
                                Daily Reflection
                            </h1>
                            <p className="text-lg text-white/70 max-w-md">
                                Take a moment to pause, breathe, and reflect on your day.
                            </p>
                            <Button
                                size="lg"
                                onClick={handleStart}
                                className="mt-8 rounded-full px-10 py-6 text-lg bg-white/10 backdrop-blur-sm border border-white/20 text-white hover:bg-white/20 hover:scale-105 transition-all duration-300"
                            >
                                <Sparkles className="h-5 w-5 mr-2" />
                                {loading ? "Preparing..." : "Start Reflection"}
                            </Button>
                        </motion.div>
                    )}

                    {/* Question Cards */}
                    {currentQuestion && (
                        <QuestionCard
                            key={currentQuestion.id}
                            question={currentQuestion}
                            onAnswer={handleAnswer}
                        />
                    )}

                    {/* Completion Screen */}
                    {step === "complete" && (
                        <motion.div
                            key="complete"
                            initial={{ opacity: 0, y: 40 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6 }}
                            className="flex flex-col items-center gap-8 text-center"
                        >
                            <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                                className="w-20 h-20 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center"
                            >
                                <Sparkles className="h-10 w-10 text-white" />
                            </motion.div>

                            <h2 className="text-3xl md:text-4xl font-light text-white">
                                Reflection Saved
                            </h2>
                            <p className="text-lg text-white/70 max-w-md">
                                Thank you for taking time to reflect. Your insights have been recorded.
                            </p>

                            <Button
                                size="lg"
                                onClick={handleBack}
                                className="mt-4 rounded-full px-8 py-6 text-lg bg-white/10 backdrop-blur-sm border border-white/20 text-white hover:bg-white/20"
                            >
                                Return to Dashboard
                            </Button>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Progress indicator */}
                {typeof step === "number" && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="absolute bottom-8 flex gap-2"
                    >
                        {questions.map((_, index) => (
                            <div
                                key={index}
                                className={`w-2 h-2 rounded-full transition-all duration-300 ${index <= step
                                    ? "bg-white"
                                    : "bg-white/30"
                                    }`}
                            />
                        ))}
                    </motion.div>
                )}
            </div>
        </div>
    );
}
