"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Settings,
  FileText,
  LogOut,
  User,
  Brain,
} from "lucide-react";
import Image from "next/image";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export interface ProfileData {
  name?: string;
  email?: string;
  avatar?: string;
  model?: string;
}

interface MenuItem {
  label: string;
  value?: string;
  icon: React.ReactNode;
  onClick?: () => void;
  href?: string;
}

interface ProfileDropdownProps extends React.HTMLAttributes<HTMLDivElement> {
  profile?: ProfileData;
  onSignOut?: () => void;
}

export function ProfileDropdown({
  profile,
  onSignOut,
  className,
  ...props
}: ProfileDropdownProps) {
  const router = useRouter();
  const [isOpen, setIsOpen] = React.useState(false);

  // Use provided profile or fallback to empty strings
  const userName = profile?.name || "User";
  const userEmail = profile?.email || "";
  const userAvatar = profile?.avatar;

  const handleSecondBrain = () => {
    router.push("/app/second-brain");
    setIsOpen(false);
  };

  const menuItems: MenuItem[] = [
    {
      label: "Profile",
      icon: <User className="w-4 h-4" />,
      href: "/app/profile",
    },
    {
      label: "Second Brain",
      value: "Graph",
      icon: <Brain className="w-4 h-4" />,
      onClick: handleSecondBrain,
    },
    {
      label: "Settings",
      icon: <Settings className="w-4 h-4" />,
      href: "/app/settings",
    },
    {
      label: "Terms & Policies",
      icon: <FileText className="w-4 h-4" />,
      href: "/app/terms",
    },
  ];

  return (
    <div className={cn("relative", className)} {...props}>
      <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
        <div className="group relative">
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-3 p-2.5 rounded-xl bg-background border border-border/60 hover:border-border hover:bg-accent/50 hover:shadow-sm transition-all duration-200 focus:outline-none"
            >
              <div className="text-left flex-1 hidden sm:block">
                <div className="text-sm font-medium text-foreground tracking-tight leading-tight">
                  {userName}
                </div>
                {userEmail && (
                  <div className="text-xs text-muted-foreground tracking-tight leading-tight">
                    {userEmail}
                  </div>
                )}
              </div>
              <div className="relative">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/80 to-primary p-[2px]">
                  <div className="w-full h-full rounded-full overflow-hidden bg-background flex items-center justify-center">
                    {userAvatar ? (
                      <Image
                        src={userAvatar}
                        alt={userName}
                        width={32}
                        height={32}
                        className="w-full h-full object-cover rounded-full"
                      />
                    ) : (
                      <User className="w-5 h-5 text-muted-foreground" />
                    )}
                  </div>
                </div>
              </div>
            </button>
          </DropdownMenuTrigger>

          {/* Bending line indicator on the right */}
          <div
            className={cn(
              "absolute -right-2 top-1/2 -translate-y-1/2 transition-all duration-200 hidden sm:block",
              isOpen
                ? "opacity-100"
                : "opacity-60 group-hover:opacity-100"
            )}
          >
            <svg
              width="10"
              height="20"
              viewBox="0 0 10 20"
              fill="none"
              className={cn(
                "transition-all duration-200",
                isOpen
                  ? "text-primary scale-110"
                  : "text-muted-foreground group-hover:text-foreground"
              )}
              aria-hidden="true"
            >
              <path
                d="M2 4C5 8 5 12 2 16"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                fill="none"
              />
            </svg>
          </div>

          <DropdownMenuContent
            align="end"
            sideOffset={8}
            className="w-60 p-2 bg-popover/95 backdrop-blur-sm border border-border rounded-xl shadow-lg"
          >
            <div className="space-y-1">
              {menuItems.map((item) => (
                <DropdownMenuItem
                  key={item.label}
                  className="p-0 focus:bg-transparent"
                >
                  <button
                    type="button"
                    onClick={item.onClick}
                    className="flex items-center w-full p-2.5 hover:bg-accent rounded-lg transition-all duration-200 cursor-pointer group"
                  >
                    <div className="flex items-center gap-2 flex-1">
                      <span className="text-muted-foreground group-hover:text-foreground transition-colors">
                        {item.icon}
                      </span>
                      <span className="text-sm font-medium text-foreground">
                        {item.label}
                      </span>
                    </div>
                    {item.value && (
                      <span className="text-xs font-medium rounded-md py-0.5 px-2 bg-secondary text-secondary-foreground">
                        {item.value}
                      </span>
                    )}
                  </button>
                </DropdownMenuItem>
              ))}
            </div>

            <DropdownMenuSeparator className="my-2 bg-border" />

            <DropdownMenuItem className="p-0 focus:bg-transparent">
              <button
                type="button"
                onClick={onSignOut}
                className="w-full flex items-center gap-3 p-2.5 rounded-lg hover:bg-destructive/10 cursor-pointer transition-all group"
              >
                <LogOut className="w-4 h-4 text-destructive" />
                <span className="text-sm font-medium text-destructive">
                  Sign Out
                </span>
              </button>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </div>
      </DropdownMenu>
    </div>
  );
}
