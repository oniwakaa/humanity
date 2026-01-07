const API_BASE = "http://127.0.0.1:8000";

export interface Entry {
    id: string;
    text: string;
    feature_type: string;
    tags: string[];
    created_at: string;
}

export interface EntryResponse {
    id: string;
    message: string;
}

export interface DailySubmission {
    cycle_id: string;
    answers: Record<string, any>[];
}

export const api = {
    // Health Check
    checkHealth: async () => {
        const res = await fetch(`${API_BASE}/health`);
        return res.json();
    },

    // Entries (Diary/Story)
    createEntry: async (text: string, tags: string[] = []): Promise<EntryResponse> => {
        const res = await fetch(`${API_BASE}/entry`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, tags }),
        });
        if (!res.ok) throw new Error("Failed to create entry");
        return res.json();
    },

    // Story Specific
    startStorySession: async () => {
        const res = await fetch(`${API_BASE}/story/start`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to start story");
        return res.json();
    },

    stopStorySession: async (): Promise<EntryResponse> => {
        const res = await fetch(`${API_BASE}/story/stop`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to stop story");
        return res.json();
    },

    // Daily Reflection
    submitDaily: async (cycleId: string, answers: Record<string, any>[]) => {
        const res = await fetch(`${API_BASE}/daily/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cycle_id: cycleId, answers }),
        });
        if (!res.ok) throw new Error("Failed to submit daily reflection");
        return res.json();
    },

    generateQuestions: async () => {
        const res = await fetch(`${API_BASE}/daily/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });
        if (!res.ok) throw new Error("Failed to generate questions");
        return res.json();
    },

    // Chat
    chat: async (message: string, context: any[] = []) => {
        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, context }),
        });
        if (!res.ok) throw new Error("Chat failed");
        return res.json();
    },

    saveDiary: async (transcript: { role: string, content: string }[]) => {
        const res = await fetch(`${API_BASE}/diary/save`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ transcript }),
        });
        if (!res.ok) throw new Error("Failed to save diary");
        return res.json();
    }
};
