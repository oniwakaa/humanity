"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { X, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ChatMessageBubble } from "@/components/diary/chat-message";
import type { ChatMessage } from "@/types/diary";

interface ChatHistoryProps {
    title: string;
    date: string;
    messages: Array<{ role: string; content: string }>;
    onClose: () => void;
}

/**
 * Read-only chat history view.
 * Reuses ChatMessageBubble for consistent styling, without input box.
 */
export function ChatHistory({ title, date, messages, onClose }: ChatHistoryProps) {
    // Convert to ChatMessage format
    const formattedMessages: ChatMessage[] = messages.map((msg, index) => ({
        id: `msg-${index}`,
        role: msg.role as "user" | "assistant",
        content: msg.content,
        timestamp: new Date(),
    }));

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] bg-background/95 backdrop-blur-sm"
        >
            <div className="h-full flex flex-col max-w-2xl mx-auto">
                {/* Header */}
                <header className="flex items-center justify-between px-4 py-4 border-b border-border/50">
                    <div className="flex items-center gap-3">
                        <BookOpen className="h-5 w-5 text-muted-foreground" />
                        <div>
                            <h2 className="font-medium text-foreground">{title}</h2>
                            <p className="text-xs text-muted-foreground">{date}</p>
                        </div>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={onClose}
                        className="rounded-full"
                    >
                        <X className="h-5 w-5" />
                    </Button>
                </header>

                {/* Messages - Read Only */}
                <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
                    {formattedMessages.length > 0 ? (
                        formattedMessages.map((message) => (
                            <ChatMessageBubble
                                key={message.id}
                                message={message}
                                isStreaming={false}
                            />
                        ))
                    ) : (
                        <div className="text-center text-muted-foreground py-12">
                            <p>No messages in this conversation.</p>
                        </div>
                    )}
                </div>

                {/* Footer - No Input (Read-Only) */}
                <footer className="px-4 py-3 border-t border-border/50">
                    <p className="text-center text-xs text-muted-foreground">
                        This is a read-only view of a past conversation
                    </p>
                </footer>
            </div>
        </motion.div>
    );
}
