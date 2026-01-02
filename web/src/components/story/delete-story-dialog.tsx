"use client";

import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface DeleteStoryDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    storyTitle: string;
    onConfirm: () => void;
}

export function DeleteStoryDialog({
    open,
    onOpenChange,
    storyTitle,
    onConfirm,
}: DeleteStoryDialogProps) {
    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Delete Story</AlertDialogTitle>
                    <AlertDialogDescription>
                        Are you sure you want to delete &quot;{storyTitle}&quot;? This action
                        cannot be undone and the story will be permanently removed.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={onConfirm}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                        Delete
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
