"use client";

import * as React from "react";
import { MoreVertical, Trash2, FileEdit } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import type { Story } from "@/types/story";

interface StoryCardProps {
    story: Story;
    onDelete: (storyId: string) => void;
    onEdit?: (storyId: string) => void;
    className?: string;
}

function formatDate(date: Date): string {
    return new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
    }).format(date);
}

export function StoryCard({ story, onDelete, onEdit, className }: StoryCardProps) {
    const isDraft = story.status === "draft";

    const handleCardClick = () => {
        if (isDraft && onEdit) {
            onEdit(story.id);
        }
    };

    return (
        <article
            onClick={handleCardClick}
            className={cn(
                "group relative rounded-xl border border-border bg-card p-5 transition-all duration-200",
                "hover:border-primary/20 hover:shadow-md hover:shadow-primary/5",
                isDraft && "cursor-pointer",
                className
            )}
        >
            {/* Header with title and menu */}
            <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <h3 className="text-lg font-semibold text-foreground leading-tight truncate">
                            {story.title}
                        </h3>
                        {isDraft && (
                            <span className="inline-flex items-center rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400 ring-1 ring-inset ring-amber-500/20">
                                Draft
                            </span>
                        )}
                    </div>
                    <time
                        dateTime={story.createdAt.toISOString()}
                        className="mt-1 block text-sm text-muted-foreground"
                    >
                        {formatDate(story.updatedAt || story.createdAt)}
                    </time>
                </div>

                {/* Three-dot menu */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={(e) => e.stopPropagation()}
                            className="h-8 w-8 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity focus:opacity-100"
                            aria-label="Story options"
                        >
                            <MoreVertical className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        {isDraft && onEdit && (
                            <DropdownMenuItem
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onEdit(story.id);
                                }}
                            >
                                <FileEdit className="mr-2 h-4 w-4" />
                                Edit
                            </DropdownMenuItem>
                        )}
                        <DropdownMenuItem
                            onClick={(e) => {
                                e.stopPropagation();
                                onDelete(story.id);
                            }}
                            className="text-destructive focus:text-destructive focus:bg-destructive/10"
                        >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            {/* AI Summary */}
            <p className="mt-3 text-sm text-muted-foreground leading-relaxed line-clamp-3">
                {story.summary}
            </p>
        </article>
    );
}
