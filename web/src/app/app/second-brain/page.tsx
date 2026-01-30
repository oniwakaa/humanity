"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BGPattern } from "@/components/ui/bg-pattern";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { GraphView } from "@/components/second-brain/graph-view";
import { ProfileDropdown } from "@/components/ui/profile-dropdown";
import {
  generateMockGraphData,
  GraphData,
  GraphNode,
} from "@/components/second-brain/graph-data";
import { ArrowLeft, Network, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";

export default function SecondBrainPage() {
  const router = useRouter();
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [profile, setProfile] = useState<{ name: string; email: string } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Load user profile
    const profileStr = localStorage.getItem("user_profile");
    if (profileStr) {
      try {
        const parsed = JSON.parse(profileStr);
        setProfile({
          name: parsed.firstName || parsed.name || "Traveller",
          email: parsed.email || "",
        });
      } catch {
        setProfile({ name: "Traveller", email: "" });
      }
    }

    // TODO: Replace with actual API call to fetch graph data from backend
    // For now, using mock data for development/testing
    const loadGraphData = async () => {
      setIsLoading(true);
      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 500));
      setGraphData(generateMockGraphData());
      setIsLoading(false);
    };

    loadGraphData();
  }, []);

  const handleNodeClick = (node: GraphNode) => {
    // TODO: Handle node click - could navigate to entry detail, filter by tag, etc.
    console.log("Node clicked:", node);
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    // TODO: Replace with actual API call
    await new Promise((resolve) => setTimeout(resolve, 500));
    setGraphData(generateMockGraphData());
    setIsLoading(false);
  };

  return (
    <div className="relative min-h-screen w-full overflow-hidden">
      {/* Background Pattern */}
      <BGPattern
        variant="grid"
        mask="fade-edges"
        className="text-muted-foreground/20"
        fill="currentColor"
      />

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 px-4 sm:px-6 py-4">
        <div className="mx-auto max-w-7xl flex items-center justify-between">
          {/* Back button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/app")}
            className="gap-2 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            <span className="hidden sm:inline">Back</span>
          </Button>

          {/* Title */}
          <div className="flex items-center gap-2">
            <Network className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-medium hidden sm:block">Second Brain</h1>
          </div>

          {/* Profile Dropdown */}
          <ProfileDropdown
            profile={profile || undefined}
            onSignOut={() => {
              // TODO: Implement sign out logic
              router.push("/");
            }}
          />
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto pt-20 pb-6 px-4 h-screen">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="h-full flex flex-col gap-4"
        >
          {/* Info Card */}
          <Card className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
            <div>
              <h2 className="text-lg font-medium">Your Knowledge Graph</h2>
              <p className="text-sm text-muted-foreground">
                Visualize connections between your entries, tags, and topics.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isLoading}
              className="gap-2 shrink-0"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </Card>

          {/* Graph Container */}
          <Card className="flex-1 overflow-hidden relative min-h-[500px]">
            {isLoading ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                  <p className="text-sm text-muted-foreground">Loading graph...</p>
                </div>
              </div>
            ) : graphData ? (
              <GraphView
                data={graphData}
                onNodeClick={handleNodeClick}
                className="absolute inset-0"
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center">
                <p className="text-muted-foreground">Failed to load graph data</p>
              </div>
            )}
          </Card>
        </motion.div>
      </main>
    </div>
  );
}
