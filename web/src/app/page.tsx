"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Typewriter } from "@/components/ui/typewriter-text";
import { GetStartedButton } from "@/components/ui/get-started-button";
import ProfileModal from "@/components/onboarding/profile-modal";
import SetupModal from "@/components/onboarding/setup-modal";

export default function Home() {
  const router = useRouter();
  const [showProfile, setShowProfile] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  const [backendError, setBackendError] = useState<string | null>(null);

  useEffect(() => {
    setIsClient(true);
    // Check backend status
    fetch(`${API_URL}/setup/status`)
      .then(res => res.json())
      .then(data => {
        setBackendError(null); // Clear error if successful
        const localCompleted = localStorage.getItem("onboarding_completed") === "true";
        // If backend is configured AND local marks done, we skip.
        if (data.is_configured && localCompleted) {
          router.replace("/app");
        } else if (!data.is_configured && localCompleted) {
          // Force reset local state if backend is gone
          console.log("Backend not configured, resetting local onboarding state.");
          localStorage.removeItem("onboarding_completed");
        }
      })
      .catch(err => {
        console.error("Failed to check backend status:", err);
        setBackendError(`Backend Unreachable (${API_URL}). Please ensure the server is running on port 8000.`);
      });
  }, [router]);

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

  if (!isClient) return null; // Avoid hydration mismatch

  return (
    <div className="relative flex min-h-[80vh] flex-col items-center justify-center overflow-hidden">


      <main className="z-10 flex flex-col items-center gap-6 text-center">
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

        {backendError && (
          <div className="rounded-md bg-destructive/15 p-3 text-destructive">
            <p className="text-sm font-medium">{backendError}</p>
          </div>
        )}

        <GetStartedButton onClick={handleStart} />
      </main>

      {showProfile && <ProfileModal onComplete={handleProfileComplete} />}
      {showSetup && <SetupModal onComplete={handleSetupComplete} />}
    </div>
  );
}
