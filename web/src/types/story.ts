export type StoryStatus = "saved" | "draft";

export interface Story {
    id: string;
    title: string;
    createdAt: Date;
    updatedAt: Date;
    summary: string;
    content: string;
    status: StoryStatus;
}

// Mock data for development
export const mockStories: Story[] = [
    {
        id: "story-1",
        title: "Finding My Voice",
        createdAt: new Date("2026-01-02T08:30:00"),
        updatedAt: new Date("2026-01-02T08:30:00"),
        summary:
            "Today I realized that my fear of public speaking stems from childhood experiences. Working through these emotions has been liberating.",
        content:
            "<p>Today I realized that my fear of public speaking stems from childhood experiences. Working through these emotions has been liberating.</p><p>It started when I was just eight years old...</p>",
        status: "saved",
    },
    {
        id: "story-2",
        title: "The Mountain Hike",
        createdAt: new Date("2025-12-28T14:15:00"),
        updatedAt: new Date("2025-12-28T14:15:00"),
        summary:
            "Climbed Mount Wilson last weekend with friends. The journey taught me patience and reminded me that the best views come after the hardest climbs.",
        content:
            "<p>Climbed Mount Wilson last weekend with friends. The journey taught me patience and reminded me that the best views come after the hardest climbs.</p>",
        status: "saved",
    },
    {
        id: "story-3",
        title: "Learning to Let Go",
        createdAt: new Date("2025-12-20T19:45:00"),
        updatedAt: new Date("2025-12-20T19:45:00"),
        summary:
            "Sometimes holding on does more damage than letting go. I've been practicing acceptance and finding peace in uncertainty.",
        content:
            "<p>Sometimes holding on does more damage than letting go. I've been practicing acceptance and finding peace in uncertainty.</p>",
        status: "saved",
    },
    {
        id: "story-4",
        title: "My First Marathon",
        createdAt: new Date("2025-12-15T09:00:00"),
        updatedAt: new Date("2025-12-15T09:00:00"),
        summary:
            "After months of training, I finally crossed that finish line. It wasn't about the time—it was about proving to myself that I could do hard things.",
        content:
            "<p>After months of training, I finally crossed that finish line. It wasn't about the time—it was about proving to myself that I could do hard things.</p>",
        status: "saved",
    },
    {
        id: "story-5",
        title: "Reconnecting with Dad",
        createdAt: new Date("2025-12-10T20:30:00"),
        updatedAt: new Date("2025-12-10T20:30:00"),
        summary:
            "Had a long overdue conversation with my father. We talked about old wounds and new beginnings. It's never too late to heal.",
        content:
            "<p>Had a long overdue conversation with my father. We talked about old wounds and new beginnings. It's never too late to heal.</p>",
        status: "saved",
    },
];
