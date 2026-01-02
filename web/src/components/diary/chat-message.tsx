"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import type { ChatMessage } from "@/types/diary";

interface ChatMessageBubbleProps {
    message: ChatMessage;
    isStreaming?: boolean;
    className?: string;
}

// User Message: Compact gray bubble style
function UserMessage({ message }: { message: ChatMessage }) {
    return (
        <div className="flex w-full justify-end">
            <div className="max-w-[80%] rounded-2xl bg-muted px-4 py-3">
                <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                    {message.content}
                </p>
            </div>
        </div>
    );
}

// AI Message: Narrative text without background
function AIMessage({
    message,
    isStreaming,
}: {
    message: ChatMessage;
    isStreaming: boolean;
}) {
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="w-full"
        >
            <div className="py-1">
                {isStreaming ? (
                    <TextGenerateEffect
                        words={message.content}
                        className="text-sm leading-[1.75] text-foreground font-normal"
                        duration={0.2}
                        filter={false}
                    />
                ) : (
                    <p className="text-sm leading-[1.75] text-foreground whitespace-pre-wrap">
                        {message.content}
                    </p>
                )}
            </div>
        </motion.div>
    );
}

export function ChatMessageBubble({
    message,
    isStreaming = false,
    className,
}: ChatMessageBubbleProps) {
    const isUser = message.role === "user";

    return (
        <div className={cn("w-full", className)}>
            {isUser ? (
                <UserMessage message={message} />
            ) : (
                <AIMessage message={message} isStreaming={isStreaming} />
            )}
        </div>
    );
}
