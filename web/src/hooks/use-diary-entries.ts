"use client";

import { useState, useEffect, useCallback } from "react";

export interface DiarySummary {
    id: string;
    date: string;
    title: string;
    summary: string;
}

interface UseDiaryEntriesResult {
    entries: DiarySummary[];
    isLoading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

/**
 * Hook to fetch diary entries from the backend.
 * Provides refetch function for cache invalidation after save operations.
 */
export function useDiaryEntries(limit = 20): UseDiaryEntriesResult {
    const [entries, setEntries] = useState<DiarySummary[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchEntries = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await fetch(
                `${API_BASE}/diary/entries?limit=${limit}`,
                {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );

            if (!response.ok) {
                throw new Error(`Failed to fetch entries: ${response.statusText}`);
            }

            const data: DiarySummary[] = await response.json();
            setEntries(data);
        } catch (err) {
            console.error("Error fetching diary entries:", err);
            setError(err instanceof Error ? err.message : "Failed to load entries");
        } finally {
            setIsLoading(false);
        }
    }, [limit]);

    // Fetch on mount
    useEffect(() => {
        fetchEntries();
    }, [fetchEntries]);

    return {
        entries,
        isLoading,
        error,
        refetch: fetchEntries,
    };
}
