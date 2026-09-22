"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Play, Pause, RotateCcw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface VideoTrimmerProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  videoUrl: string;
  totalDuration: number;
  startTime: number;
  trimDuration: number;
  onTrimChange: (start: number, duration: number) => void;
  maxAllowedDuration?: number;
}

export function VideoTrimmer({
  videoRef,
  videoUrl,
  totalDuration,
  startTime,
  trimDuration,
  onTrimChange,
  maxAllowedDuration = 3.0,
}: VideoTrimmerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [thumbnails, setThumbnails] = useState<string[]>([]);
  const [isPlayingSelection, setIsPlayingSelection] = useState(false);
  const [currentTime, setCurrentTime] = useState(startTime);
  const [activeDrag, setActiveDrag] = useState<"left" | "right" | "window" | null>(null);
  const dragStartXRef = useRef(0);
  const dragStartValuesRef = useRef({ start: startTime, dur: trimDuration });

  const safeTotal = Math.max(0.1, totalDuration || 1);
  const safeStart = Math.max(0, Math.min(startTime, safeTotal - 0.1));
  const safeDur = Math.max(0.1, Math.min(trimDuration, safeTotal - safeStart));
  const safeEnd = Math.min(safeTotal, safeStart + safeDur);

  const leftPercent = (safeStart / safeTotal) * 100;
  const widthPercent = (safeDur / safeTotal) * 100;
  const rightPercent = 100 - (leftPercent + widthPercent);
  const playheadPercent = (Math.max(safeStart, Math.min(currentTime, safeEnd)) / safeTotal) * 100;

  const isOverTelegramLimit = safeDur > maxAllowedDuration + 0.05;

  // Extract thumbnail snapshots for filmstrip background
  useEffect(() => {
    if (!videoUrl || safeTotal <= 0) return;

    let isCancelled = false;
    const count = 9;
    const thumbs: string[] = [];

    const offscreenVideo = document.createElement("video");
    offscreenVideo.src = videoUrl;
    offscreenVideo.crossOrigin = "anonymous";
    offscreenVideo.muted = true;
    offscreenVideo.playsInline = true;

    const canvas = document.createElement("canvas");
    canvas.width = 96;
    canvas.height = 54;
    const ctx = canvas.getContext("2d");

    const captureFrameAt = (time: number): Promise<string> => {
      return new Promise((resolve) => {
        const onSeeked = () => {
          offscreenVideo.removeEventListener("seeked", onSeeked);
          if (ctx) {
            ctx.drawImage(offscreenVideo, 0, 0, canvas.width, canvas.height);
            resolve(canvas.toDataURL("image/jpeg", 0.6));
          } else {
            resolve("");
          }
        };
        offscreenVideo.addEventListener("seeked", onSeeked);
        offscreenVideo.currentTime = Math.min(time, safeTotal - 0.05);
      });
    };

    offscreenVideo.addEventListener("loadedmetadata", async () => {
      try {
        for (let i = 0; i < count; i++) {
          if (isCancelled) break;
          const t = (safeTotal / count) * i + (safeTotal / count) * 0.5;
          const dataUrl = await captureFrameAt(t);
          if (dataUrl) thumbs.push(dataUrl);
        }
        if (!isCancelled && thumbs.length > 0) {
          setThumbnails(thumbs);
        }
      } catch {
        // Fallback: gracefully ignore canvas security errors
      }
    });

    return () => {
      isCancelled = true;
      offscreenVideo.src = "";
    };
  }, [videoUrl, safeTotal]);

  // Sync video playhead and handle selection looping
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      if (isPlayingSelection && video.currentTime >= safeEnd) {
        video.currentTime = safeStart;
        video.play().catch(() => {});
      }
    };

    const handlePause = () => {
      if (video.currentTime >= safeEnd || video.currentTime < safeStart) {
        setIsPlayingSelection(false);
      }
    };

    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("pause", handlePause);

    return () => {
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("pause", handlePause);
    };
  }, [videoRef, safeStart, safeEnd, isPlayingSelection]);

  // Pointer drag handling
  const handlePointerDown = (
    type: "left" | "right" | "window",
    e: React.PointerEvent<HTMLDivElement>
  ) => {
    e.preventDefault();
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    setActiveDrag(type);
    dragStartXRef.current = e.clientX;
    dragStartValuesRef.current = { start: safeStart, dur: safeDur };

    // Pause video while dragging for smooth scrubbing
    if (videoRef.current && !videoRef.current.paused) {
      videoRef.current.pause();
      setIsPlayingSelection(false);
    }
  };

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!activeDrag || !containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      if (rect.width <= 0) return;

      const deltaX = e.clientX - dragStartXRef.current;
      const deltaTime = (deltaX / rect.width) * safeTotal;
      const initial = dragStartValuesRef.current;

      if (activeDrag === "left") {
        let newStart = initial.start + deltaTime;
        newStart = Math.max(0, Math.min(newStart, initial.start + initial.dur - 0.2));
        const newDur = initial.start + initial.dur - newStart;
        onTrimChange(Number(newStart.toFixed(2)), Number(newDur.toFixed(2)));

        if (videoRef.current) {
          videoRef.current.currentTime = newStart;
        }
      } else if (activeDrag === "right") {
        let newEnd = initial.start + initial.dur + deltaTime;
        newEnd = Math.max(initial.start + 0.2, Math.min(newEnd, safeTotal));
        const newDur = newEnd - initial.start;
        onTrimChange(Number(initial.start.toFixed(2)), Number(newDur.toFixed(2)));

        if (videoRef.current) {
          videoRef.current.currentTime = newEnd;
        }
      } else if (activeDrag === "window") {
        let newStart = initial.start + deltaTime;
        newStart = Math.max(0, Math.min(newStart, safeTotal - initial.dur));
        onTrimChange(Number(newStart.toFixed(2)), Number(initial.dur.toFixed(2)));

        if (videoRef.current) {
          videoRef.current.currentTime = newStart;
        }
      }
    },
    [activeDrag, safeTotal, onTrimChange, videoRef]
  );

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (activeDrag) {
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // Ignore if pointer capture already released
      }
      setActiveDrag(null);
    }
  };

  // Toggle selection playback
  const togglePlaySelection = () => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlayingSelection && !video.paused) {
      video.pause();
      setIsPlayingSelection(false);
    } else {
      video.currentTime = safeStart;
      video
        .play()
        .then(() => setIsPlayingSelection(true))
        .catch(() => {});
    }
  };

  // Quick action: Snap trim duration to 3.0s max
  const handleSnapToLimit = () => {
    const newDur = Math.min(maxAllowedDuration, safeTotal - safeStart);
    onTrimChange(Number(safeStart.toFixed(2)), Number(newDur.toFixed(2)));
    if (videoRef.current) {
      videoRef.current.currentTime = safeStart;
    }
  };

  // Reset to full video or first 3s
  const handleReset = () => {
    const initialDur = Math.min(maxAllowedDuration, safeTotal);
    onTrimChange(0, Number(initialDur.toFixed(2)));
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
    }
  };

  const formatSeconds = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins}:${s < 10 ? "0" : ""}${s.toFixed(1)}s`;
  };

  return (
    <div className="space-y-2.5 pt-1 select-none">
      {/* Header bar: Duration indicator and actions */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={togglePlaySelection}
            className="h-7 px-2.5 text-xs gap-1 font-medium bg-background/80"
          >
            {isPlayingSelection ? (
              <>
                <Pause className="h-3 w-3 fill-current" /> Pause Trim
              </>
            ) : (
              <>
                <Play className="h-3 w-3 fill-current" /> Play Trim
              </>
            )}
          </Button>

          <Badge
            variant={isOverTelegramLimit ? "destructive" : "secondary"}
            className="h-6 font-mono text-[11px] px-2"
          >
            Duration: {safeDur.toFixed(2)}s {isOverTelegramLimit ? "(> 3.0s limit)" : "(Compliant)"}
          </Badge>
        </div>

        <div className="flex items-center gap-1.5">
          {isOverTelegramLimit && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleSnapToLimit}
              className="h-7 text-xs text-amber-500 border-amber-500/40 hover:bg-amber-500/10 gap-1 px-2 font-medium"
            >
              <Sparkles className="h-3 w-3" /> Fit 3.0s Max
            </Button>
          )}

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="h-7 text-xs text-muted-foreground hover:text-foreground px-2"
            title="Reset trim to 0:00"
          >
            <RotateCcw className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* QuickTime-Style Timeline Container */}
      <div
        ref={containerRef}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        className="relative h-14 w-full rounded-lg overflow-hidden border border-border/80 bg-zinc-950 touch-none cursor-pointer shadow-inner"
      >
        {/* Filmstrip thumbnails background */}
        <div className="absolute inset-0 flex">
          {thumbnails.length > 0 ? (
            thumbnails.map((src, i) => (
              <div
                key={i}
                className="flex-1 h-full bg-cover bg-center border-r border-black/30 last:border-r-0 opacity-70"
                style={{ backgroundImage: `url(${src})` }}
              />
            ))
          ) : (
            <div className="w-full h-full flex items-center justify-center text-[10px] text-zinc-500 font-mono tracking-wider">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="flex-1 text-center border-r border-zinc-800 last:border-r-0">
                  {((safeTotal / 8) * i).toFixed(1)}s
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Dimmed excluded zone (Before start) */}
        <div
          className="absolute top-0 bottom-0 left-0 bg-black/75 backdrop-blur-[1px] pointer-events-none transition-[width] duration-75"
          style={{ width: `${leftPercent}%` }}
        />

        {/* Dimmed excluded zone (After end) */}
        <div
          className="absolute top-0 bottom-0 right-0 bg-black/75 backdrop-blur-[1px] pointer-events-none transition-[width] duration-75"
          style={{ width: `${rightPercent}%` }}
        />

        {/* QuickTime Yellow Trim Window (Selection Box) */}
        <div
          onPointerDown={(e) => handlePointerDown("window", e)}
          className={`absolute top-0 bottom-0 border-y-2 cursor-grab active:cursor-grabbing transition-colors ${
            isOverTelegramLimit
              ? "border-amber-500 bg-amber-500/20"
              : "border-amber-400 bg-amber-400/15"
          }`}
          style={{
            left: `${leftPercent}%`,
            width: `${widthPercent}%`,
          }}
        >
          {/* Top duration pill */}
          <div className="absolute -top-0.5 left-1/2 -translate-x-1/2 px-1.5 py-0.5 rounded-b bg-amber-500 text-[9px] font-mono font-bold text-black shadow-sm pointer-events-none">
            {safeDur.toFixed(1)}s
          </div>

          {/* Left Handle: '[' style */}
          <div
            onPointerDown={(e) => handlePointerDown("left", e)}
            className="absolute top-0 bottom-0 left-0 w-3 -ml-1 flex items-center justify-center bg-amber-400 hover:bg-amber-300 text-black cursor-ew-resize rounded-l active:scale-105 transition-transform z-20 shadow-md"
            title="Drag to adjust clip start"
          >
            <div className="w-0.5 h-4 bg-black/60 rounded-full" />
          </div>

          {/* Right Handle: ']' style */}
          <div
            onPointerDown={(e) => handlePointerDown("right", e)}
            className="absolute top-0 bottom-0 right-0 w-3 -mr-1 flex items-center justify-center bg-amber-400 hover:bg-amber-300 text-black cursor-ew-resize rounded-r active:scale-105 transition-transform z-20 shadow-md"
            title="Drag to adjust clip end"
          >
            <div className="w-0.5 h-4 bg-black/60 rounded-full" />
          </div>
        </div>

        {/* Live Playhead needle */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white shadow-[0_0_8px_rgba(255,255,255,0.9)] pointer-events-none z-30 transition-[left] duration-75"
          style={{ left: `${playheadPercent}%` }}
        >
          <div className="w-2 h-2 rounded-full bg-white -ml-[3px] -mt-1 shadow" />
        </div>
      </div>

      {/* Footer labels: precise timestamps */}
      <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground px-0.5">
        <span>Start: {formatSeconds(safeStart)}</span>
        <span className="text-zinc-500">Total: {formatSeconds(safeTotal)}</span>
        <span>End: {formatSeconds(safeEnd)}</span>
      </div>
    </div>
  );
}
