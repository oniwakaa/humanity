"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BGPattern } from "@/components/ui/bg-pattern";
import { HumanityCard } from "@/components/dashboard/humanity-card";
import { Typewriter } from "@/components/ui/typewriter-text"; // Verify this import path aligns with existing component
import { motion } from "framer-motion";

export default function DashboardPage() {
    const router = useRouter();
    const [userName, setUserName] = useState<string>("");

    useEffect(() => {
        // Retrieve user name from localStorage on mount
        const profileStr = localStorage.getItem("user_profile");
        if (profileStr) {
            try {
                const profile = JSON.parse(profileStr);
                setUserName(profile.firstName || profile.name || "Traveller");
            } catch (e) {
                console.error("Failed to parse user profile", e);
            }
        }
    }, []);

    const features = [
        {
            title: "Your Story",
            description: "Build your personal narrative through guided voice conversations. Track your growth and milestones over time.",
            action: "Continue Story",
            gradient: [
                { color: 'rgba(255, 140, 66, 1)', stop: '10.5%' }, // Deep Amber
                { color: 'rgba(255, 110, 80, 1)', stop: '16%' },  // Orange Coral
                { color: 'rgba(255, 125, 100, 1)', stop: '17.5%' }, // Coral
                { color: 'rgba(255, 155, 130, 1)', stop: '25%' },  // Light Coral
                { color: 'rgba(255, 185, 165, 1)', stop: '40%' },  // Peach
                { color: 'rgba(255, 205, 210, 1)', stop: '65%' },  // Soft Pink
                { color: 'rgba(230, 210, 255, 1)', stop: '100%' }  // Lavender
            ],
            onClick: () => router.push("/app/story"),
        },
        {
            title: "Daily Reflection",
            description: "Deepen self-awareness with structured prompts. A quiet space to process your day and align with your values.",
            action: "Start Reflection",
            gradient: [
                { color: 'rgba(30, 60, 114, 1)', stop: '10.5%' },  // Deep Blue
                { color: 'rgba(42, 82, 152, 1)', stop: '16%' },    // Royal Blue
                { color: 'rgba(50, 110, 160, 1)', stop: '17.5%' }, // Blue Teal
                { color: 'rgba(75, 145, 180, 1)', stop: '25%' },   // Teal
                { color: 'rgba(110, 190, 190, 1)', stop: '40%' },  // Aqua
                { color: 'rgba(150, 225, 200, 1)', stop: '65%' },  // Mint
                { color: 'rgba(200, 245, 220, 1)', stop: '100%' }  // Pale Lime
            ],
            onClick: () => console.log("Navigate to Reflection"),
        },
        {
            title: "Your Diary",
            description: "Capture spontaneous thoughts and emotions freely. A private, unrestricted space for your rawest expression.",
            action: "Open Diary",
            gradient: [
                { color: 'rgba(180, 30, 90, 1)', stop: '10.5%' },  // Deep Magenta
                { color: 'rgba(215, 50, 90, 1)', stop: '16%' },    // Rose
                { color: 'rgba(240, 80, 90, 1)', stop: '17.5%' },  // Coral Red
                { color: 'rgba(255, 120, 100, 1)', stop: '25%' },  // Salmon
                { color: 'rgba(255, 170, 130, 1)', stop: '40%' },  // Apricot
                { color: 'rgba(255, 215, 160, 1)', stop: '65%' },  // Golden Yellow
                { color: 'rgba(210, 245, 180, 1)', stop: '100%' }  // Pale Lime
            ],
            onClick: () => console.log("Navigate to Diary"),
        },
    ];

    return (
        <div className="relative min-h-screen w-full overflow-hidden">
            {/* Background Pattern */}
            <BGPattern
                variant="grid"
                mask="fade-edges"
                className="text-muted-foreground/20"
                fill="currentColor"
            />

            <main className="container mx-auto flex min-h-screen flex-col items-center justify-center px-4 py-20 relative z-10">

                {/* Welcome Header */}
                <div className="mb-20 text-center">
                    <h1 className="text-3xl md:text-5xl font-medium tracking-tight text-foreground">
                        <Typewriter
                            key={userName}
                            text={[`Welcome, ${userName || "..."}`]}
                            speed={70}
                            cursor="|"
                            loop={false}
                            delay={500}
                        />
                    </h1>
                    <p className="mt-4 text-muted-foreground text-lg">
                        What would you like to explore today?
                    </p>
                </div>

                {/* 3D Cards Grid */}
                <div className="grid w-full max-w-6xl gap-8 md:grid-cols-3">
                    {features.map((feature, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.5 + index * 0.1, duration: 0.5 }}
                            className="flex justify-center"
                        >
                            <HumanityCard
                                title={feature.title}
                                subtitle={feature.description}
                                gradientColors={feature.gradient}
                                actionText={feature.action}
                                onClick={feature.onClick}
                            />
                        </motion.div>
                    ))}
                </div>
            </main>
        </div>
    );
}

