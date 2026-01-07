"use client";

import * as React from "react";
import { useRef, useCallback, useState } from "react";
import HTMLFlipBook from "react-pageflip";
import { ChevronLeft, ChevronRight, X, Plus, PenLine, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ChatHistory } from "@/components/diary/chat-history";

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
function SummaryPage({
    summary,
    onViewChat
}: {
    summary: ChatSummary;
    onViewChat: (id: string) => void;
}) {
    return (
        <div className="h-full flex flex-col text-stone-800">
            <div className="mb-6">
                <span className="text-sm uppercase tracking-widest text-stone-500">
                    {summary.date}
                </span>
            </div>

            <h3 className="font-serif text-2xl font-semibold mb-6 text-stone-900">
                {summary.title}
            </h3>

            <p className="font-serif text-lg leading-loose text-stone-700 flex-1">
                {summary.summary}
            </p>

            <div className="mt-auto pt-4">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onViewChat(summary.id)}
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
            <div className="text-center space-y-8">
                <p className="font-serif text-xl italic text-stone-600">
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

    // Chat History Modal State
    const [selectedChat, setSelectedChat] = useState<{
        id: string;
        title: string;
        date: string;
        messages: any[];
    } | null>(null);
    const [isLoadingChat, setIsLoadingChat] = useState(false);

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

    const handleViewChat = useCallback(async (id: string) => {
        // Find summary info immediately for partial data
        const summary = summaries.find(s => s.id === id);
        if (!summary) return;

        setIsLoadingChat(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/diary/entries/${id}`);
            if (!response.ok) throw new Error("Failed to fetch chat");

            const data = await response.json();
            setSelectedChat({
                id: data.id,
                title: data.title,
                date: data.date,
                messages: data.transcript || []
            });
        } catch (error) {
            console.error("Error loading chat:", error);
            // Fallback or error toast in real app
        } finally {
            setIsLoadingChat(false);
        }
    }, [summaries]);

    return (
        <div className="h-full flex flex-col relative">
            {/* Chat History Modal */}
            <AnimatePresence>
                {selectedChat && (
                    <ChatHistory
                        title={selectedChat.title}
                        date={selectedChat.date}
                        messages={selectedChat.messages}
                        onClose={() => setSelectedChat(null)}
                    />
                )}
            </AnimatePresence>

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
                <div className="relative max-h-[95vh]">
                    {/* @ts-ignore - react-pageflip types */}
                    <HTMLFlipBook
                        ref={bookRef}
                        width={550}
                        height={750}
                        size="stretch"
                        minWidth={400}
                        maxWidth={600}
                        minHeight={560}
                        maxHeight={850}
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
                                <SummaryPage
                                    summary={summary}
                                    onViewChat={handleViewChat}
                                />
                                {isLoadingChat && (
                                    <div className="absolute inset-0 bg-white/50 flex items-center justify-center">
                                        <Loader2 className="h-6 w-6 animate-spin text-amber-600" />
                                    </div>
                                )}
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
