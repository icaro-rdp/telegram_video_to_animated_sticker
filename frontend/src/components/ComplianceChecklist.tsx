"use client";

import { Check, X, AlertTriangle, ShieldCheck } from "lucide-react";
import { MediaInfo } from "@/lib/api";

interface ComplianceChecklistProps {
  info: MediaInfo;
  mode: "sticker" | "emoji";
  valid: boolean;
  issues: string[];
}

export function ComplianceChecklist({
  info,
  mode,
  valid,
  issues,
}: ComplianceChecklistProps) {
  const isSticker = mode === "sticker";

  const dimensionPassed = isSticker
    ? Math.max(info.width, info.height) === 512 && Math.min(info.width, info.height) <= 512
    : info.width === 100 && info.height === 100;

  const durationPassed = (info.duration || 0) <= 3.05;
  const sizePassed = (info.size_bytes || 0) <= 256 * 1024;
  const codecPassed = info.codec.toLowerCase() === "vp9";
  const audioPassed = !info.has_audio;

  const checkItems = [
    {
      title: "Video Codec",
      requirement: "VP9 (.webm)",
      actual: info.codec.toUpperCase(),
      passed: codecPassed,
    },
    {
      title: "Dimensions",
      requirement: isSticker ? "One side 512px (other ≤ 512px)" : "Exactly 100x100px",
      actual: `${info.width} × ${info.height}px`,
      passed: dimensionPassed,
    },
    {
      title: "Duration",
      requirement: "≤ 3.00 seconds",
      actual: `${info.duration ? info.duration.toFixed(2) : "0.00"}s`,
      passed: durationPassed,
    },
    {
      title: "File Size",
      requirement: "≤ 256.0 KB",
      actual: `${info.size_kb ? info.size_kb.toFixed(1) : "0.0"} KB`,
      passed: sizePassed,
    },
    {
      title: "Audio Stream",
      requirement: "No audio tracks",
      actual: audioPassed ? "None" : "Audio detected",
      passed: audioPassed,
    },
    {
      title: "Alpha Channel",
      requirement: "YUVA420P / Transparency",
      actual: info.has_alpha ? "Alpha preserved" : "No alpha",
      passed: true, // Non-fatal
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-sky-500" />
          <h3 className="text-sm font-semibold text-foreground">
            Telegram Compliance Verification
          </h3>
        </div>
        {valid ? (
          <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
            <Check className="h-3 w-3" /> Fully Compliant
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-500 border border-rose-500/20">
            <AlertTriangle className="h-3 w-3" /> Needs Attention
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
        {checkItems.map((item, idx) => (
          <div
            key={idx}
            className={`p-2.5 rounded-lg border flex items-center justify-between transition-colors ${
              item.passed
                ? "bg-card/50 border-border/50"
                : "bg-rose-500/5 border-rose-500/30"
            }`}
          >
            <div>
              <div className="font-medium text-foreground">{item.title}</div>
              <div className="text-[11px] text-muted-foreground">{item.requirement}</div>
            </div>
            <div className="flex items-center gap-1.5 font-mono">
              <span
                className={`text-[11px] font-semibold ${
                  item.passed ? "text-foreground" : "text-rose-400"
                }`}
              >
                {item.actual}
              </span>
              {item.passed ? (
                <div className="h-4 w-4 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center">
                  <Check className="h-2.5 w-2.5" />
                </div>
              ) : (
                <div className="h-4 w-4 rounded-full bg-rose-500/20 text-rose-500 flex items-center justify-center">
                  <X className="h-2.5 w-2.5" />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {issues && issues.length > 0 && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs space-y-1">
          <div className="font-semibold flex items-center gap-1">
            <AlertTriangle className="h-3.5 w-3.5" /> Telegram Bot Compatibility Issues:
          </div>
          <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
            {issues.map((issue, idx) => (
              <li key={idx}>{issue}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
