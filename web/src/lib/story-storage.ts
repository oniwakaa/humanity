import type { Story, StoryStatus } from "@/types/story";

const STORAGE_KEY = "humanity_stories";

function parseStoredStories(data: string): Story[] {
    try {
        const parsed = JSON.parse(data);
        return parsed.map((s: Record<string, unknown>) => ({
            ...s,
            createdAt: new Date(s.createdAt as string),
            updatedAt: new Date(s.updatedAt as string),
        }));
    } catch {
        return [];
    }
}

export function getStories(): Story[] {
    if (typeof window === "undefined") return [];

    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
        return [];
    }

    return parseStoredStories(stored);
}

export function getStoryById(id: string): Story | undefined {
    const stories = getStories();
    return stories.find((s) => s.id === id);
}

export function saveStory(story: Story): void {
    const stories = getStories();
    const existingIndex = stories.findIndex((s) => s.id === story.id);

    if (existingIndex >= 0) {
        stories[existingIndex] = story;
    } else {
        stories.push(story);
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(stories));
}

export function deleteStory(id: string): void {
    const stories = getStories();
    const filtered = stories.filter((s) => s.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
}

export function getStoriesByStatus(status: StoryStatus): Story[] {
    return getStories().filter((s) => s.status === status);
}

export function generateId(): string {
    return `story-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export function generateSummary(content: string): string {
    // Strip HTML tags and get first ~150 characters
    const text = content.replace(/<[^>]*>/g, "").trim();
    if (text.length <= 150) return text;
    return text.substring(0, 147) + "...";
}
