"use client";

import * as React from "react";
import { useState } from "react";
import { Book } from "@/components/ui/book";
import { cn } from "@/lib/utils";

interface DiaryBookCoverProps {
    onClick?: () => void;
    className?: string;
}

export function DiaryBookCover({ onClick, className }: DiaryBookCoverProps) {
    const [isHovered, setIsHovered] = useState(false);

    return (
        <div
            className={cn("cursor-pointer relative", className)}
            onClick={onClick}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                    onClick?.();
                }
            }}
        >
            <Book
                color="#8B4513"
                textColor="#F5F5DC"
                texture={true}
                depth={10}
                width={380}
                variant="default"
            >
                <div className="p-8 flex flex-col items-center justify-center h-full text-center">
                    <div className="space-y-4">
                        <h2
                            className="text-3xl font-serif font-semibold tracking-wide"
                            style={{ color: "var(--text-color, #F5F5DC)" }}
                        >
                            My Diary
                        </h2>
                        <div
                            className="w-20 h-0.5 mx-auto opacity-60"
                            style={{ backgroundColor: "var(--text-color, #F5F5DC)" }}
                        />
                        <p
                            className="text-base font-serif italic opacity-80"
                            style={{ color: "var(--text-color, #F5F5DC)" }}
                        >
                            A journey of reflection
                        </p>
                    </div>
                </div>
            </Book>

            {/* Inside pages peek effect on hover */}
            <div
                className={cn(
                    "absolute right-0 top-1/2 -translate-y-1/2 transition-all duration-500 ease-out pointer-events-none",
                    isHovered ? "opacity-100 translate-x-2" : "opacity-0 translate-x-0"
                )}
                style={{
                    width: "12px",
                    height: "calc(100% - 20px)",
                    background: `repeating-linear-gradient(
            90deg,
            #fff 0px,
            #f5f5f0 1px,
            #fff 2px,
            #e8e8e0 3px
          )`,
                    boxShadow: "inset 2px 0 4px rgba(0,0,0,0.1)",
                    borderRadius: "0 2px 2px 0",
                }}
            />

            {/* Second layer of pages for depth */}
            <div
                className={cn(
                    "absolute right-0 top-1/2 -translate-y-1/2 transition-all duration-300 delay-75 ease-out pointer-events-none",
                    isHovered ? "opacity-80 translate-x-4" : "opacity-0 translate-x-0"
                )}
                style={{
                    width: "8px",
                    height: "calc(100% - 30px)",
                    background: `repeating-linear-gradient(
            90deg,
            #f8f8f5 0px,
            #eeeeea 1px,
            #f8f8f5 2px
          )`,
                    boxShadow: "inset 2px 0 3px rgba(0,0,0,0.08)",
                    borderRadius: "0 2px 2px 0",
                }}
            />
        </div>
    );
}
