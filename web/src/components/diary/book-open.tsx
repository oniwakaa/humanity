"use client";

import * as React from "react";
import { useRef, useCallback, useState } from "react";
import HTMLFlipBook from "react-pageflip";
import { ChevronLeft, ChevronRight, X, Plus, PenLine } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChatSummary {
    id: string;
    date: string;
    title: string;
    summary: string;
}

interface DiaryBookOpenProps {
    summaries: ChatSummary[];
    onClose: () => void;
    onNewEntry: () => void;
}

// Individual page component
const DiaryPage = React.forwardRef<
    HTMLDivElement,
    { children: React.ReactNode; className?: string }
>(({ children, className }, ref) => (
    <div
        ref={ref}
        className={cn(
            "bg-amber-50 dark:bg-amber-100 h-full w-full p-8 overflow-hidden",
            "shadow-inner border border-amber-200/50",
            className
        )}
        style={{
            backgroundImage: `
        linear-gradient(90deg, transparent 79px, #abced4 79px, #abced4 81px, transparent 81px),
        linear-gradient(#eee .1em, transparent .1em)
      `,
            backgroundSize: "100% 1.5em",
        }}
    >
        {children}
    </div>
));
DiaryPage.displayName = "DiaryPage";

// Summary page content
function SummaryPage({ summary }: { summary: ChatSummary }) {
    return (
        <div className="h-full flex flex-col text-stone-800">
            <div className="mb-4">
                <span className="text-xs uppercase tracking-widest text-stone-500">
                    {summary.date}
                </span>
            </div>

            <h3 className="font-serif text-xl font-semibold mb-4 text-stone-900">
                {summary.title}
            </h3>

            <p className="font-serif text-base leading-relaxed text-stone-700 flex-1">
                {summary.summary}
            </p>

            <div className="mt-auto pt-4">
                <Button
                    variant="ghost"
                    size="sm"
                    className="text-stone-600 hover:text-stone-900 hover:bg-amber-100/50"
                >
                    View Full Chat →
                </Button>
            </div>
        </div>
    );
}

// New entry page
function NewEntryPage({ onNewEntry }: { onNewEntry: () => void }) {
    return (
        <div className="h-full flex flex-col items-center justify-center text-stone-800">
            <div className="text-center space-y-6">
                <p className="font-serif text-lg italic text-stone-600">
                    Dear Diary...
                </p>

                <Button
                    onClick={onNewEntry}
                    size="lg"
                    className="rounded-full w-16 h-16 bg-amber-600 hover:bg-amber-700 shadow-lg"
                >
                    <Plus className="h-8 w-8" />
                </Button>

                <p className="text-sm text-stone-500">
                    Start a new entry
                </p>
            </div>
        </div>
    );
}

export function DiaryBookOpen({
    summaries,
    onClose,
    onNewEntry,
}: DiaryBookOpenProps) {
    const bookRef = useRef<any>(null);
    const [currentPage, setCurrentPage] = useState(0);
    const totalPages = summaries.length + 1; // +1 for new entry page

    const handleFlip = useCallback((e: { data: number }) => {
        setCurrentPage(e.data);
    }, []);

    const flipPrev = useCallback(() => {
        bookRef.current?.pageFlip()?.flipPrev();
    }, []);

    const flipNext = useCallback(() => {
        bookRef.current?.pageFlip()?.flipNext();
    }, []);

    const skipToNewEntry = useCallback(() => {
        bookRef.current?.pageFlip()?.flip(totalPages - 1);
    }, [totalPages]);

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <motion.header
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between px-4 py-3 border-b border-border/50"
            >
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                    className="gap-2"
                >
                    <X className="h-4 w-4" />
                    <span className="hidden sm:inline">Close</span>
                </Button>

                <span className="text-sm text-muted-foreground">
                    Page {currentPage + 1} of {totalPages}
                </span>

                <Button
                    variant="outline"
                    size="sm"
                    onClick={skipToNewEntry}
                    className="gap-2"
                    disabled={currentPage === totalPages - 1}
                >
                    <PenLine className="h-4 w-4" />
                    <span className="hidden sm:inline">New Entry</span>
                </Button>
            </motion.header>

            {/* Book Content */}
            <div className="flex-1 flex items-center justify-center p-4 sm:p-8">
                <div className="relative">
                    {/* @ts-ignore - react-pageflip types */}
                    <HTMLFlipBook
                        ref={bookRef}
                        width={320}
                        height={450}
                        size="stretch"
                        minWidth={280}
                        maxWidth={500}
                        minHeight={400}
                        maxHeight={600}
                        showCover={false}
                        mobileScrollSupport={true}
                        onFlip={handleFlip}
                        className="shadow-2xl"
                        style={{}}
                        startPage={0}
                        drawShadow={true}
                        flippingTime={600}
                        usePortrait={true}
                        startZIndex={0}
                        autoSize={true}
                        maxShadowOpacity={0.5}
                        showPageCorners={true}
                        disableFlipByClick={false}
                        swipeDistance={30}
                        clickEventForward={true}
                        useMouseEvents={true}
                    >
                        {/* Summary Pages */}
                        {summaries.map((summary) => (
                            <DiaryPage key={summary.id}>
                                <SummaryPage summary={summary} />
                            </DiaryPage>
                        ))}

                        {/* New Entry Page */}
                        <DiaryPage>
                            <NewEntryPage onNewEntry={onNewEntry} />
                        </DiaryPage>
                    </HTMLFlipBook>
                </div>
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-center gap-4 py-4">
                <Button
                    variant="outline"
                    size="icon"
                    onClick={flipPrev}
                    disabled={currentPage === 0}
                    className="rounded-full"
                >
                    <ChevronLeft className="h-5 w-5" />
                </Button>

                <span className="text-sm text-muted-foreground min-w-[100px] text-center">
                    {currentPage < summaries.length
                        ? summaries[currentPage]?.title
                        : "New Entry"}
                </span>

                <Button
                    variant="outline"
                    size="icon"
                    onClick={flipNext}
                    disabled={currentPage >= totalPages - 1}
                    className="rounded-full"
                >
                    <ChevronRight className="h-5 w-5" />
                </Button>
            </div>
        </div>
    );
}
