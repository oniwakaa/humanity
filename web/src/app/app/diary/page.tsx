"use client";

import * as React from "react";
import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { PromptInputBox } from "@/components/ui/ai-prompt-box";
import { ChatMessageBubble } from "@/components/diary/chat-message";
import type { ChatMessage } from "@/types/diary";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const INITIAL_MESSAGE: ChatMessage = {
    id: "welcome",
    role: "assistant",
    content:
        "Welcome to your Open Diary. This is a safe space for reflection. Share what's on your mind, and I'll help guide your thoughts with meaningful questions.",
    timestamp: new Date(),
};

export default function OpenDiaryPage() {
    const router = useRouter();
    const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
    const [isLoading, setIsLoading] = useState(false);
    const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const [isSaving, setIsSaving] = useState(false);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleSave = async () => {
        if (messages.length <= 1) return; // Don't save empty chats (just welcome msg)

        setIsSaving(true);
        try {
            const { api } = await import("@/lib/api");
            const transcript = messages.map(m => ({
                role: m.role,
                content: m.content
            }));
            await api.saveDiary(transcript);
            console.log("Diary saved successfully");
            // Optionally clear messages or show toast
        } catch (e) {
            console.error("Failed to save diary:", e);
        } finally {
            setIsSaving(false);
        }
    };

    const handleBack = async () => {
        // Auto-save on exit
        await handleSave();
        router.push("/app");
    };

    const generateMessageId = () => {
        return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    };

    const handleSend = useCallback(async (message: string, files?: File[]) => {
        if (!message.trim() || isLoading) return;

        // Ignore file uploads for now
        void files;

        const userMessage: ChatMessage = {
            id: generateMessageId(),
            role: "user",
            content: message.trim(),
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setIsLoading(true);

        // Create placeholder for AI response
        const aiMessageId = generateMessageId();
        const aiMessage: ChatMessage = {
            id: aiMessageId,
            role: "assistant",
            content: "",
            timestamp: new Date(),
        };
        setMessages((prev) => [...prev, aiMessage]);
        setStreamingMessageId(aiMessageId);

        try {
            const response = await fetch(`${API_URL}/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    message: userMessage.content,
                    context: messages.slice(-10).map((m) => ({
                        role: m.role,
                        content: m.content,
                    })),
                }),
            });

            if (!response.ok) {
                throw new Error("Failed to get response");
            }

            const data = await response.json();
            const aiContent = data.response || data.message || "I'm here to listen. Could you tell me more?";

            // Update AI message with response
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === aiMessageId
                        ? { ...m, content: aiContent, timestamp: new Date() }
                        : m
                )
            );
        } catch (error) {
            console.error("Chat error:", error);
            // Fallback response on error
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === aiMessageId
                        ? {
                            ...m,
                            content:
                                "I'm having trouble connecting right now. Please try again in a moment.",
                            timestamp: new Date(),
                        }
                        : m
                )
            );
        } finally {
            setIsLoading(false);
            setStreamingMessageId(null);
        }
    }, [isLoading, messages]);

    return (
        <div className="fixed inset-0 bg-background flex flex-col">
            {/* Header */}
            <motion.header
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="sticky top-0 z-20 border-b border-border/50 bg-background"
            >
                <div className="flex items-center justify-between px-4 py-3 md:px-6">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleBack}
                        disabled={isSaving}
                        className="gap-2 text-muted-foreground hover:text-foreground"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        <span className="hidden sm:inline">Back</span>
                    </Button>

                    <h1 className="text-lg font-semibold text-foreground">Open Diary</h1>

                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSave().then(() => router.push("/app"))}
                        disabled={isSaving || messages.length <= 1}
                        className="gap-2"
                    >
                        {isSaving ? "Saving..." : "Save Entry"}
                    </Button>
                </div>
            </motion.header>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 pb-40">
                <div className="mx-auto max-w-2xl space-y-4">
                    {messages.map((message, index) => (
                        <motion.div
                            key={message.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3, delay: index === messages.length - 1 ? 0.1 : 0 }}
                        >
                            <ChatMessageBubble
                                message={message}
                                isStreaming={message.id === streamingMessageId && message.content.length > 0}
                            />
                        </motion.div>
                    ))}

                    {/* Loading indicator */}
                    {isLoading && streamingMessageId && messages.find((m) => m.id === streamingMessageId)?.content === "" && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="flex justify-start"
                        >
                            <div className="bg-muted rounded-2xl px-4 py-3">
                                <div className="flex items-center gap-1">
                                    <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce" style={{ animationDelay: "0ms" }} />
                                    <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce" style={{ animationDelay: "150ms" }} />
                                    <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce" style={{ animationDelay: "300ms" }} />
                                </div>
                            </div>
                        </motion.div>
                    )}

                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Floating Input Area */}
            <div className="fixed bottom-0 left-0 right-0 pb-8 px-4 md:px-8 pointer-events-none">
                <div className="mx-auto max-w-2xl pointer-events-auto">
                    <PromptInputBox
                        onSend={handleSend}
                        isLoading={isLoading}
                        placeholder="Share your thoughts..."
                        className="shadow-2xl"
                    />
                </div>
            </div>
        </div>
    );
}
