"use client";

import * as React from "react";
import { useRef, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Plus, BookOpen, FileText, FilePenLine, ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";
import { BGPattern } from "@/components/ui/bg-pattern";
import { Button } from "@/components/ui/button";
import { ScrollButton } from "@/components/ui/scroll-button";
import { StoryCard } from "@/components/story/story-card";
import { DeleteStoryDialog } from "@/components/story/delete-story-dialog";
import { getStories, deleteStory as deleteStoryFromStorage } from "@/lib/story-storage";
import type { Story, StoryStatus } from "@/types/story";

type TabValue = "saved" | "drafts";

export default function StoryListPage() {
    const router = useRouter();
    const [stories, setStories] = useState<Story[]>([]);
    const [deleteTarget, setDeleteTarget] = useState<Story | null>(null);
    const [activeTab, setActiveTab] = useState<TabValue>("saved");

    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const scrollEndRef = useRef<HTMLDivElement>(null);

    // Load stories from localStorage
    useEffect(() => {
        setStories(getStories());
    }, []);

    // Filter and sort stories
    const filteredStories = stories
        .filter((s) => (activeTab === "saved" ? s.status === "saved" : s.status === "draft"))
        .sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());

    const savedCount = stories.filter((s) => s.status === "saved").length;
    const draftCount = stories.filter((s) => s.status === "draft").length;

    const handleDeleteRequest = (storyId: string) => {
        const story = stories.find((s) => s.id === storyId);
        if (story) {
            setDeleteTarget(story);
        }
    };

    const handleDeleteConfirm = () => {
        if (deleteTarget) {
            deleteStoryFromStorage(deleteTarget.id);
            setStories((prev) => prev.filter((s) => s.id !== deleteTarget.id));
            setDeleteTarget(null);
        }
    };

    const handleAddNewStory = () => {
        router.push("/app/story/new");
    };

    const handleEditStory = useCallback(
        (storyId: string) => {
            router.push(`/app/story/new?edit=${storyId}`);
        },
        [router]
    );

    const handleBack = () => {
        router.push("/app");
    };

    return (
        <div className="relative min-h-screen w-full overflow-hidden">
            {/* Background Pattern */}
            <BGPattern
                variant="grid"
                mask="fade-edges"
                className="text-muted-foreground/20"
                fill="currentColor"
            />

            <div className="relative z-10 mx-auto flex min-h-screen max-w-3xl flex-col px-4 py-8 md:py-12">
                {/* Header */}
                <header className="mb-6">
                    {/* Back Button */}
                    <motion.div
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3 }}
                        className="mb-4"
                    >
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={handleBack}
                            className="gap-2 text-muted-foreground hover:text-foreground -ml-2"
                        >
                            <ArrowLeft className="h-4 w-4" />
                            Back to Dashboard
                        </Button>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4 }}
                    >
                        <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-foreground">
                            Your Story
                        </h1>
                        <p className="mt-2 text-muted-foreground">
                            Browse your personal narratives and life experiences.
                        </p>
                    </motion.div>

                    {/* Add New Story Button */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.1 }}
                        className="mt-6"
                    >
                        <Button onClick={handleAddNewStory} size="lg" className="gap-2">
                            <Plus className="h-5 w-5" />
                            Add New Story
                        </Button>
                    </motion.div>
                </header>

                {/* Tabs */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3, delay: 0.2 }}
                    className="mb-6"
                >
                    <div className="inline-flex items-center rounded-lg border border-border bg-muted/50 p-1">
                        <button
                            onClick={() => setActiveTab("saved")}
                            className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all ${activeTab === "saved"
                                ? "bg-background text-foreground shadow-sm"
                                : "text-muted-foreground hover:text-foreground"
                                }`}
                        >
                            <FileText className="h-4 w-4" />
                            Saved
                            {savedCount > 0 && (
                                <span className="ml-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                                    {savedCount}
                                </span>
                            )}
                        </button>
                        <button
                            onClick={() => setActiveTab("drafts")}
                            className={`inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all ${activeTab === "drafts"
                                ? "bg-background text-foreground shadow-sm"
                                : "text-muted-foreground hover:text-foreground"
                                }`}
                        >
                            <FilePenLine className="h-4 w-4" />
                            Drafts
                            {draftCount > 0 && (
                                <span className="ml-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-600 dark:text-amber-400">
                                    {draftCount}
                                </span>
                            )}
                        </button>
                    </div>
                </motion.div>

                {/* Scrollable Story List */}
                <div className="relative flex-1">
                    <div
                        ref={scrollContainerRef}
                        className="h-[calc(100vh-360px)] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent"
                    >
                        {filteredStories.length > 0 ? (
                            <div className="space-y-4 pb-4">
                                {filteredStories.map((story, index) => (
                                    <motion.div
                                        key={story.id}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.3, delay: index * 0.05 }}
                                    >
                                        <StoryCard
                                            story={story}
                                            onDelete={handleDeleteRequest}
                                            onEdit={handleEditStory}
                                        />
                                    </motion.div>
                                ))}
                                <div ref={scrollEndRef} />
                            </div>
                        ) : (
                            /* Empty State */
                            <motion.div
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ duration: 0.4 }}
                                className="flex flex-col items-center justify-center py-20 text-center"
                            >
                                <div className="rounded-full bg-muted p-4">
                                    <BookOpen className="h-8 w-8 text-muted-foreground" />
                                </div>
                                <h2 className="mt-4 text-lg font-medium text-foreground">
                                    {activeTab === "saved" ? "No saved stories yet" : "No drafts"}
                                </h2>
                                <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                                    {activeTab === "saved"
                                        ? "Start capturing your personal narrative. Your saved stories will appear here."
                                        : "Drafts are automatically saved when you navigate away from the editor without saving."}
                                </p>
                                <Button
                                    onClick={handleAddNewStory}
                                    variant="outline"
                                    className="mt-6 gap-2"
                                >
                                    <Plus className="h-4 w-4" />
                                    Write a New Story
                                </Button>
                            </motion.div>
                        )}
                    </div>

                    {/* Scroll Button */}
                    <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
                        <ScrollButton
                            scrollRef={scrollEndRef}
                            containerRef={scrollContainerRef}
                            threshold={100}
                            variant="secondary"
                        />
                    </div>
                </div>
            </div>

            {/* Delete Confirmation Dialog */}
            <DeleteStoryDialog
                open={deleteTarget !== null}
                onOpenChange={(open) => {
                    if (!open) setDeleteTarget(null);
                }}
                storyTitle={deleteTarget?.title ?? ""}
                onConfirm={handleDeleteConfirm}
            />
        </div>
    );
}
