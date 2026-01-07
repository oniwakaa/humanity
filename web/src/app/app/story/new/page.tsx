"use client";

import * as React from "react";
import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { StoryEditor } from "@/components/story/story-editor";
import {
    getStoryById,
    saveStory,
    generateId,
    generateSummary,
} from "@/lib/story-storage";
import type { Story } from "@/types/story";

function NewStoryContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const editId = searchParams.get("edit");

    const [title, setTitle] = useState("");
    const [content, setContent] = useState("");
    const [storyId, setStoryId] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);
    const hasUnsavedChanges = useRef(false);

    // Load draft if editing
    useEffect(() => {
        if (editId) {
            const existingStory = getStoryById(editId);
            if (existingStory) {
                setStoryId(existingStory.id);
                setTitle(existingStory.title);
                setContent(existingStory.content);
            }
        }
    }, [editId]);

    // Track unsaved changes
    useEffect(() => {
        hasUnsavedChanges.current = title.trim() !== "" || content.trim() !== "";
    }, [title, content]);

    const saveDraft = useCallback(() => {
        if (!hasUnsavedChanges.current) return;

        const id = storyId || generateId();
        const now = new Date();

        const draft: Story = {
            id,
            title: title.trim() || "Untitled Draft",
            content,
            summary: generateSummary(content) || "No content yet...",
            createdAt: storyId ? (getStoryById(storyId)?.createdAt ?? now) : now,
            updatedAt: now,
            status: "draft",
        };

        saveStory(draft);
        // Original code called saveStory(draft). 
        // Let's check original code. 
        // Line 62: saveStory(draft);
        saveStory(draft);
        setStoryId(id);
    }, [title, content, storyId]);

    const handleBack = useCallback(() => {
        // Auto-save as draft if there's unsaved content
        if (hasUnsavedChanges.current) {
            saveDraft();
        }
        router.push("/app/story");
    }, [router, saveDraft]);

    const handleSave = useCallback(() => {
        if (!title.trim() && !content.trim()) {
            router.push("/app/story");
            return;
        }

        setIsSaving(true);

        const id = storyId || generateId();
        const now = new Date();

        const story: Story = {
            id,
            title: title.trim() || "Untitled Story",
            content,
            summary: generateSummary(content) || "No summary available.",
            createdAt: storyId ? (getStoryById(storyId)?.createdAt ?? now) : now,
            updatedAt: now,
            status: "saved",
        };

        saveStory(story);
        hasUnsavedChanges.current = false;

        setTimeout(() => {
            router.push("/app/story");
        }, 300);
    }, [title, content, storyId, router]);

    return (
        <div className="fixed inset-0 bg-background overflow-hidden flex flex-col">
            {/* Full-width Header */}
            <motion.header
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="sticky top-0 z-20 w-full border-b border-border/50 bg-background"
            >
                <div className="flex w-full items-center justify-between px-4 py-3 md:px-6">
                    {/* Left: Back Button */}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleBack}
                        className="gap-2 text-muted-foreground hover:text-foreground"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        <span className="hidden sm:inline">Back</span>
                    </Button>

                    {/* Right: Save Button */}
                    <Button
                        onClick={handleSave}
                        size="sm"
                        disabled={isSaving}
                    >
                        {isSaving ? "Saving..." : "Save"}
                    </Button>
                </div>
            </motion.header>

            {/* Full-page Editor Area */}
            <main className="flex-1 overflow-y-auto">
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.4, delay: 0.1 }}
                    className="min-h-full"
                >
                    <StoryEditor
                        title={title}
                        onTitleChange={setTitle}
                        content={content}
                        onContentChange={setContent}
                    />
                </motion.div>
            </main>
        </div>
    );
}

export default function NewStoryPage() {
    return (
        <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Loading editor...</div>}>
            <NewStoryContent />
        </Suspense>
    );
}
