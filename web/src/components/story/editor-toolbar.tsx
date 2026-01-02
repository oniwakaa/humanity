"use client";

import { type Editor } from "@tiptap/react";
import {
    Bold,
    Italic,
    Underline,
    Heading1,
    Heading2,
    Heading3,
    List,
    ListOrdered,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface EditorToolbarProps {
    editor: Editor | null;
    className?: string;
}

interface ToolbarButtonProps {
    onClick: () => void;
    isActive?: boolean;
    disabled?: boolean;
    children: React.ReactNode;
    title: string;
}

function ToolbarButton({
    onClick,
    isActive,
    disabled,
    children,
    title,
}: ToolbarButtonProps) {
    return (
        <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClick}
            disabled={disabled}
            title={title}
            className={cn(
                "h-8 w-8 p-0",
                isActive && "bg-muted text-foreground"
            )}
        >
            {children}
        </Button>
    );
}

export function EditorToolbar({ editor, className }: EditorToolbarProps) {
    if (!editor) return null;

    return (
        <div
            className={cn(
                "flex items-center gap-1 border-b border-border px-2 py-1.5",
                className
            )}
        >
            {/* Text formatting */}
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleBold().run()}
                isActive={editor.isActive("bold")}
                disabled={!editor.can().chain().focus().toggleBold().run()}
                title="Bold"
            >
                <Bold className="h-4 w-4" />
            </ToolbarButton>

            <ToolbarButton
                onClick={() => editor.chain().focus().toggleItalic().run()}
                isActive={editor.isActive("italic")}
                disabled={!editor.can().chain().focus().toggleItalic().run()}
                title="Italic"
            >
                <Italic className="h-4 w-4" />
            </ToolbarButton>

            <ToolbarButton
                onClick={() => editor.chain().focus().toggleUnderline().run()}
                isActive={editor.isActive("underline")}
                disabled={!editor.can().chain().focus().toggleUnderline().run()}
                title="Underline"
            >
                <Underline className="h-4 w-4" />
            </ToolbarButton>

            <div className="mx-2 h-4 w-px bg-border" />

            {/* Headings */}
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                isActive={editor.isActive("heading", { level: 1 })}
                title="Heading 1"
            >
                <Heading1 className="h-4 w-4" />
            </ToolbarButton>

            <ToolbarButton
                onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                isActive={editor.isActive("heading", { level: 2 })}
                title="Heading 2"
            >
                <Heading2 className="h-4 w-4" />
            </ToolbarButton>

            <ToolbarButton
                onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
                isActive={editor.isActive("heading", { level: 3 })}
                title="Heading 3"
            >
                <Heading3 className="h-4 w-4" />
            </ToolbarButton>

            <div className="mx-2 h-4 w-px bg-border" />

            {/* Lists */}
            <ToolbarButton
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                isActive={editor.isActive("bulletList")}
                title="Bullet List"
            >
                <List className="h-4 w-4" />
            </ToolbarButton>

            <ToolbarButton
                onClick={() => editor.chain().focus().toggleOrderedList().run()}
                isActive={editor.isActive("orderedList")}
                title="Numbered List"
            >
                <ListOrdered className="h-4 w-4" />
            </ToolbarButton>
        </div>
    );
}
