"use client";

import { useEffect, useState } from "react";
import { Zap, Server, CheckCircle2, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { checkApiStatus } from "@/lib/api";

interface HeaderProps {
  activeTab: "single" | "batch";
  onTabChange: (tab: "single" | "batch") => void;
  showBatchSelector?: boolean;
}

export function Header({
  activeTab,
  onTabChange,
  showBatchSelector = false,
}: HeaderProps) {
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function ping() {
      try {
        await checkApiStatus();
        if (isMounted) setApiConnected(true);
      } catch {
        if (isMounted) setApiConnected(false);
      }
    }
    ping();
    const interval = setInterval(ping, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="border-b border-border/40 bg-card/60 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-sky-500/20">
            <Zap className="h-5 w-5 fill-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-foreground">
                Telegram Sticker Studio
              </h1>
              <Badge variant="secondary" className="text-[11px] font-mono font-medium">
                VP9 WebM
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Official Telegram-compliant animated stickers & custom emoji
            </p>
          </div>
        </div>

        {/* Controls & Nav */}
        <div className="flex items-center justify-between md:justify-end gap-3">
          {/* API Health */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-border/60 text-xs bg-muted/40">
            <Server className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground hidden sm:inline">Backend:</span>
            {apiConnected === null ? (
              <span className="text-muted-foreground animate-pulse">Checking...</span>
            ) : apiConnected ? (
              <span className="inline-flex items-center gap-1 text-emerald-500 font-medium">
                <CheckCircle2 className="h-3.5 w-3.5" /> Online
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-rose-500 font-medium">
                <AlertCircle className="h-3.5 w-3.5" /> Offline
              </span>
            )}
          </div>

          {/* Mode Switcher (hidden for now) */}
          {showBatchSelector && (
            <div className="inline-flex p-1 rounded-lg bg-muted border border-border/50 text-xs font-medium">
              <button
                onClick={() => onTabChange("single")}
                className={`px-3 py-1.5 rounded-md transition-all ${
                  activeTab === "single"
                    ? "bg-background text-foreground shadow-sm font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Single Video
              </button>
              <button
                onClick={() => onTabChange("batch")}
                className={`px-3 py-1.5 rounded-md transition-all ${
                  activeTab === "batch"
                    ? "bg-background text-foreground shadow-sm font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Folder Batch
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
