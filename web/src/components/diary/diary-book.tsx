"use client";

import * as React from "react";
import { useState, useCallback, lazy, Suspense } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DiaryBookCover } from "@/components/diary/book-cover";
import { DiaryBookOpen } from "@/components/diary/book-open";

// Mock chat summaries - replace with real data fetch
const mockChatSummaries = [
    {
        id: "1",
        date: "January 1, 2026",
        title: "New Year Reflections",
        summary: "Reflected on the past year's achievements and set intentions for the new year. Explored feelings of gratitude and hope for what's to come.",
    },
    {
        id: "2",
        date: "December 28, 2025",
        title: "Finding Balance",
        summary: "Discussed the challenge of maintaining work-life balance during the holiday season. Discovered strategies for staying present with family.",
    },
    {
        id: "3",
        date: "December 20, 2025",
        title: "Letting Go",
        summary: "Explored the difficulty of releasing old habits and patterns. Recognized the courage it takes to embrace change and growth.",
    },
];

interface DiaryBookProps {
    className?: string;
}

export function DiaryBook({ className }: DiaryBookProps) {
    const router = useRouter();
    const [isOpen, setIsOpen] = useState(false);

    const handleOpenBook = useCallback(() => {
        setIsOpen(true);
    }, []);

    const handleCloseBook = useCallback(() => {
        setIsOpen(false);
    }, []);

    const handleNewEntry = useCallback(() => {
        router.push("/app/diary");
    }, [router]);

    const handleBack = useCallback(() => {
        router.push("/app");
    }, [router]);

    return (
        <div className={className}>
            <AnimatePresence mode="wait">
                {!isOpen ? (
                    <motion.div
                        key="cover"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 1.1 }}
                        transition={{ duration: 0.4, ease: "easeOut" }}
                        className="flex flex-col items-center justify-center min-h-screen"
                    >
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleBack}
                            className="absolute top-4 left-4 gap-2 text-muted-foreground hover:text-foreground z-10"
                        >
                            <ArrowLeft className="h-4 w-4" />
                            <span className="hidden sm:inline">Back</span>
                        </Button>

                        <motion.div
                            whileHover={{ scale: 1.02 }}
                            transition={{ type: "spring", stiffness: 300 }}
                        >
                            <DiaryBookCover onClick={handleOpenBook} />
                        </motion.div>

                        <p className="mt-6 text-sm text-muted-foreground">
                            Click to open your diary
                        </p>
                    </motion.div>
                ) : (
                    <motion.div
                        key="open"
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        transition={{ duration: 0.5, ease: "easeOut" }}
                        className="fixed inset-0 z-50 bg-background"
                    >
                        <DiaryBookOpen
                            summaries={mockChatSummaries}
                            onClose={handleCloseBook}
                            onNewEntry={handleNewEntry}
                        />
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
