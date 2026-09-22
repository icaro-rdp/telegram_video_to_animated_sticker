"use client";

import { useState } from "react";
import { Header } from "@/components/Header";
import { SingleConverter } from "@/components/SingleConverter";
import { BatchConverter } from "@/components/BatchConverter";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"single" | "batch">("single");

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-sky-500/20 selection:text-sky-400">
      <Header activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === "single" ? <SingleConverter /> : <BatchConverter />}
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 py-6 bg-card/20 text-xs text-muted-foreground mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>
            Telegram Sticker Studio &bull; Official VP9 WebM specifications (512px max, &le; 3s, &le; 256KB, 30 FPS, no audio).
          </p>
          <div className="flex items-center gap-4">
            <a
              href="https://core.telegram.org/stickers/webm-vp9-encoding"
              target="_blank"
              rel="noreferrer"
              className="hover:text-foreground transition-colors hover:underline"
            >
              Telegram VP9 Docs
            </a>
            <a
              href="https://t.me/Stickers"
              target="_blank"
              rel="noreferrer"
              className="hover:text-foreground transition-colors hover:underline"
            >
              @Stickers Bot
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
