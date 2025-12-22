"use client";

import * as React from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { GradientBackground } from "@/components/ui/noisy-gradient-backgrounds";

export interface HumanityCardProps {
    title: string;
    subtitle: string;
    gradientColors: { color: string; stop: string }[];
    actionText: string;
    href?: string;
    onClick?: () => void;
    className?: string;
}

export const HumanityCard = React.forwardRef<HTMLDivElement, HumanityCardProps>(
    ({ title, subtitle, gradientColors, actionText, href = "#", onClick, className }, ref) => {
        const mouseX = useMotionValue(0);
        const mouseY = useMotionValue(0);

        const springConfig = { damping: 15, stiffness: 150 };
        const springX = useSpring(mouseX, springConfig);
        const springY = useSpring(mouseY, springConfig);

        const rotateX = useTransform(springY, [-0.5, 0.5], ["10.5deg", "-10.5deg"]);
        const rotateY = useTransform(springX, [-0.5, 0.5], ["-10.5deg", "10.5deg"]);

        const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const { width, height, left, top } = rect;
            const mouseXVal = e.clientX - left;
            const mouseYVal = e.clientY - top;
            const xPct = mouseXVal / width - 0.5;
            const yPct = mouseYVal / height - 0.5;
            mouseX.set(xPct);
            mouseY.set(yPct);
        };

        const handleMouseLeave = () => {
            mouseX.set(0);
            mouseY.set(0);
        };

        return (
            <motion.div
                ref={ref}
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
                style={{
                    rotateX,
                    rotateY,
                    transformStyle: "preserve-3d",
                }}
                className={cn(
                    "relative h-[26rem] w-full rounded-2xl bg-transparent transition-all duration-200",
                    className
                )}
            >
                <div
                    style={{
                        transform: "translateZ(50px)",
                        transformStyle: "preserve-3d",
                    }}
                    className="absolute inset-4 grid h-[calc(100%-2rem)] w-[calc(100%-2rem)] grid-rows-[1fr_auto] rounded-xl shadow-xl overflow-hidden"
                >
                    {/* Gradient Background with Content */}
                    <GradientBackground
                        enableNoise={true}
                        noisePatternAlpha={15}
                        colors={gradientColors}
                        className="h-full w-full"
                    >
                        {/* Darkening overlay for text contrast */}
                        <div className="absolute inset-0 h-full w-full bg-black/10" />

                        {/* Content */}
                        <div className="relative flex flex-col justify-between p-6 text-white h-full z-10">
                            <div className="flex items-start justify-between gap-4">
                                <div>
                                    <motion.h2
                                        style={{ transform: "translateZ(50px)" }}
                                        className="text-2xl font-bold leading-tight"
                                    >
                                        {title}
                                    </motion.h2>
                                    <motion.p
                                        style={{ transform: "translateZ(40px)" }}
                                        className="mt-2 text-sm font-medium text-white/90 leading-relaxed"
                                    >
                                        {subtitle}
                                    </motion.p>
                                </div>
                                {href && href !== "#" && (
                                    <motion.a
                                        href={href}
                                        whileHover={{ scale: 1.1, rotate: "2.5deg" }}
                                        whileTap={{ scale: 0.9 }}
                                        style={{ transform: "translateZ(60px)" }}
                                        className="flex-shrink-0 flex h-10 w-10 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm ring-1 ring-inset ring-white/30 transition-colors hover:bg-white/30"
                                    >
                                        <ArrowUpRight className="h-5 w-5 text-white" />
                                    </motion.a>
                                )}
                            </div>

                            <motion.button
                                onClick={onClick}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                style={{ transform: "translateZ(40px)" }}
                                className="mt-auto w-full rounded-lg py-3 text-center font-semibold text-white bg-white/20 backdrop-blur-md ring-1 ring-inset ring-white/30 hover:bg-white/30 transition-all"
                            >
                                {actionText}
                            </motion.button>
                        </div>
                    </GradientBackground>
                </div>
            </motion.div>
        );
    }
);
HumanityCard.displayName = "HumanityCard";
