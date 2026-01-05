"use client";

import * as React from "react";
import { useState, useCallback, lazy, Suspense } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DiaryBookCover } from "@/components/diary/book-cover";
import { DiaryBookOpen } from "@/components/diary/book-open";
import { useDiaryEntries } from "@/hooks/use-diary-entries";

interface DiaryBookProps {
    className?: string;
}

export function DiaryBook({ className }: DiaryBookProps) {
    const router = useRouter();
    const [isOpen, setIsOpen] = useState(false);
    const { entries, isLoading, error, refetch } = useDiaryEntries();

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

    // Refetch entries when returning from diary creation
    const handleRefresh = useCallback(async () => {
        await refetch();
    }, [refetch]);

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
                        {isLoading ? (
                            <div className="h-full flex items-center justify-center">
                                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                            </div>
                        ) : (
                            <DiaryBookOpen
                                summaries={entries}
                                onClose={handleCloseBook}
                                onNewEntry={handleNewEntry}
                            />
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
