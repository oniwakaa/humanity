"use client";

import * as React from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Placeholder from "@tiptap/extension-placeholder";
import UnderlineExtension from "@tiptap/extension-underline";
import { EditorToolbar } from "./editor-toolbar";
import { cn } from "@/lib/utils";

interface StoryEditorProps {
    title: string;
    onTitleChange: (title: string) => void;
    content: string;
    onContentChange: (content: string) => void;
    className?: string;
}

export function StoryEditor({
    title,
    onTitleChange,
    content,
    onContentChange,
    className,
}: StoryEditorProps) {
    const editor = useEditor({
        extensions: [
            StarterKit.configure({
                heading: {
                    levels: [1, 2, 3],
                },
            }),
            Placeholder.configure({
                placeholder: "Tell your story...",
                emptyEditorClass:
                    "before:content-[attr(data-placeholder)] before:text-muted-foreground before:float-left before:h-0 before:pointer-events-none",
            }),
            UnderlineExtension,
        ],
        content: content,
        immediatelyRender: false,
        editorProps: {
            attributes: {
                class:
                    "prose prose-neutral dark:prose-invert max-w-none min-h-[60vh] focus:outline-none",
            },
        },
        onUpdate: ({ editor }) => {
            onContentChange(editor.getHTML());
        },
    });

    return (
        <div className={cn("flex flex-col min-h-full bg-background", className)}>
            {/* Floating Toolbar - centered above content */}
            <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm border-b border-border/50">
                <div className="mx-auto max-w-3xl px-4 md:px-8">
                    <EditorToolbar editor={editor} className="border-0 px-0" />
                </div>
            </div>

            {/* Content Area - centered with readable max-width */}
            <div className="flex-1 mx-auto w-full max-w-3xl px-4 md:px-8 py-8 md:py-12">
                {/* Title Input - Seamless H1 style */}
                <input
                    type="text"
                    value={title}
                    onChange={(e) => onTitleChange(e.target.value)}
                    placeholder="Title"
                    className="w-full bg-transparent text-4xl md:text-5xl font-bold text-foreground placeholder:text-muted-foreground/50 focus:outline-none leading-tight tracking-tight"
                />

                {/* Subtle separator */}
                <div className="my-6 h-px bg-border/30" />

                {/* Editor Content - Continuous document flow */}
                <EditorContent editor={editor} className="flex-1" />
            </div>
        </div>
    );
}
