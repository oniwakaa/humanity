import { useState, useEffect } from "react";

const MAX_RETRIES = 30; // 15 seconds total (at 500ms interval)
const RETRY_INTERVAL = 500;
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

interface HealthStatus {
    isOnline: boolean;
    isConfigured: boolean;
    isChecking: boolean;
    error: string | null;
    retryCount?: number;
    lastErrorType?: 'network' | 'cors' | 'timeout' | 'unknown';
}

export function useBackendHealth() {
    const [status, setStatus] = useState<HealthStatus>({
        isOnline: false,
        isConfigured: false,
        isChecking: true,
        error: null
    });

    useEffect(() => {
        let attempts = 0;
        let mounted = true;

        const checkHealth = async () => {
            try {
                // We use /setup/status because it tells us if backend is responsive AND if it's set up
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

                const res = await fetch(`${API_URL}/setup/status`, {
                    signal: controller.signal,
                    mode: 'cors',
                    credentials: 'omit'
                });
                clearTimeout(timeoutId);

                if (!res.ok) throw new Error(`HTTP ${res.status}`);

                const data = await res.json();

                if (mounted) {
                    console.log('[Backend Health] Connected successfully:', data);
                    setStatus({
                        isOnline: true,
                        isConfigured: data.is_configured,
                        isChecking: false,
                        error: null,
                        retryCount: attempts
                    });
                }
                return true; // Success
            } catch (e: any) {
                // Detailed error logging
                const errorType = e.name === 'AbortError' ? 'timeout' :
                    e.message?.includes('CORS') ? 'cors' :
                        e.message?.includes('Failed to fetch') ? 'network' : 'unknown';

                console.warn(`[Backend Health] Attempt ${attempts + 1}/${MAX_RETRIES} failed:`, {
                    error: e.message,
                    type: errorType,
                    url: API_URL
                });

                if (mounted && attempts === MAX_RETRIES - 1) {
                    setStatus(prev => ({
                        ...prev,
                        lastErrorType: errorType
                    }));
                }
                return false;
            }
        };

        const poll = async () => {
            while (attempts < MAX_RETRIES && mounted) {
                const success = await checkHealth();
                if (success) return;

                attempts++;
                if (attempts === MAX_RETRIES) {
                    if (mounted) {
                        const errorHint = status.lastErrorType === 'cors' ? ' (CORS error)' :
                            status.lastErrorType === 'timeout' ? ' (timeout)' :
                                status.lastErrorType === 'network' ? ' (network error)' : '';

                        setStatus(prev => ({
                            ...prev,
                            isOnline: false,
                            isChecking: false,
                            error: `Backend Unreachable (${API_URL}) after ${MAX_RETRIES} attempts${errorHint}. Is it running?`,
                            retryCount: attempts
                        }));

                        console.error('[Backend Health] Failed to connect after all retries:', {
                            url: API_URL,
                            attempts: MAX_RETRIES,
                            lastErrorType: status.lastErrorType
                        });
                    }
                } else {
                    // Wait before retry
                    await new Promise(r => setTimeout(r, RETRY_INTERVAL));
                }
            }
        };

        poll();

        return () => { mounted = false; };
    }, []);

    return status;
}
