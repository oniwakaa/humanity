"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Typewriter } from "@/components/ui/typewriter-text";
import { GetStartedButton } from "@/components/ui/get-started-button";
import { DottedSurface } from "@/components/ui/dotted-surface";
import ProfileModal from "@/components/onboarding/profile-modal";
import SetupModal from "@/components/onboarding/setup-modal";
import { useBackendHealth } from "@/hooks/use-backend-health"; // Import Hook

export default function Home() {
  const router = useRouter();
  const [showProfile, setShowProfile] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  const [backendError, setBackendError] = useState<string | null>(null);

  const [isStabilizing, setIsStabilizing] = useState(false); // New state

  const { isOnline, isConfigured, isChecking, error } = useBackendHealth();

  useEffect(() => {
    setIsClient(true);

    if (isOnline) {
      if (isConfigured) {
        // Auto-redirect if healthy and configured
        const localCompleted = localStorage.getItem("onboarding_completed") === "true";
        if (localCompleted) {
          router.replace("/app");
        }
      } else {
        // Online but not configured: Start 60s stabilization timer
        setIsStabilizing(true);
        const timer = setTimeout(() => {
          setIsStabilizing(false);
        }, 60000); // 1 minute delay
        return () => clearTimeout(timer);
      }
    }

    // Check local consistency
    if (isOnline && !isConfigured && localStorage.getItem("onboarding_completed") === "true") {
      console.log("Backend not configured, resetting local onboarding state.");
      localStorage.removeItem("onboarding_completed");
    }

  }, [isOnline, isConfigured, router]);

  const handleStart = () => {
    setShowProfile(true);
  };

  const handleProfileComplete = (data: any) => {
    localStorage.setItem("user_profile", JSON.stringify(data));
    setShowProfile(false);
    setShowSetup(true);
  };

  const handleSetupComplete = async (setupData: any) => {
    const profileStr = localStorage.getItem("user_profile");
    const profileData = profileStr ? JSON.parse(profileStr) : {};

    const payload = {
      ollama_url: setupData.ollamaUrl,
      chat_model: setupData.chatModel,
      embed_model: setupData.embedModel,
      qdrant_url: setupData.qdrantUrl,
      stt_path: setupData.sttPath,
      profile: profileData
    };

    try {
      const res = await fetch(`${API_URL}/setup/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Setup failed to save to backend');

      localStorage.setItem("app_config", JSON.stringify(setupData));
      localStorage.setItem("onboarding_completed", "true");
      setShowSetup(false);
      router.push("/app");
    } catch (e) {
      console.error(e);
      alert(`Failed to save setup: ${e}. Is backend running?`);
    }
  };

  if (!isClient) return null;

  return (
    <div className="relative flex min-h-[80vh] flex-col items-center justify-center overflow-hidden">
      <DottedSurface />

      <main className="z-10 flex flex-col items-center gap-6 text-center">
        {/* ... Header ... */}
        <div className="flex flex-col items-center justify-center space-y-4">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-medium tracking-tight">
            <Typewriter
              text={["Welcome to Humanity"]}
              speed={70}
              cursor="|"
              loop={false}
              delay={2000}
            />
          </h1>
          <p className="text-muted-foreground text-sm md:text-base max-w-[500px]">
            Your local AI companion. Private, secure, and always by your side.
          </p>
        </div>

        {isChecking && (
          <div className="flex flex-col items-center gap-2 text-muted-foreground animate-pulse">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p className="text-sm">Connecting to Brain...</p>
          </div>
        )}

        {!isChecking && isStabilizing && (
          <div className="flex flex-col items-center gap-2 text-muted-foreground animate-pulse">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p className="text-sm">Adding last tweaks...</p>
          </div>
        )}

        {error && (
          <div className="rounded-md bg-destructive/15 p-3 text-destructive">
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        <GetStartedButton onClick={handleStart} disabled={isChecking || isStabilizing || !!error} />

      </main>

      {/* ... Modals ... */}
      {showProfile && <ProfileModal onComplete={handleProfileComplete} />}
      {showSetup && <SetupModal onComplete={handleSetupComplete} />}
    </div>
  );
}
