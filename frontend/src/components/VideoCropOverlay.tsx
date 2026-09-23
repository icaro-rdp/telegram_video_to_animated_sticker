"use client";

import React, { useCallback, useRef } from "react";
import { Maximize2, RotateCcw, Crosshair } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export interface CropBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type AspectRatioMode = "1:1" | "free" | "4:5" | "16:9";

interface VideoCropOverlayProps {
  videoWidth: number;
  videoHeight: number;
  cropBox: CropBox;
  onChange: (newCrop: CropBox) => void;
  aspectRatio: AspectRatioMode;
  onAspectRatioChange: (mode: AspectRatioMode) => void;
  children: React.ReactNode;
}

type DragType =
  | "move"
  | "nw"
  | "ne"
  | "sw"
  | "se"
  | "n"
  | "s"
  | "e"
  | "w";

export function VideoCropOverlay({
  videoWidth,
  videoHeight,
  cropBox,
  onChange,
  aspectRatio,
  onAspectRatioChange,
  children,
}: VideoCropOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeDragRef = useRef<{
    type: DragType;
    startX: number;
    startY: number;
    startCrop: CropBox;
  } | null>(null);

  const getTargetRatio = (mode: AspectRatioMode): number | null => {
    switch (mode) {
      case "1:1":
        return 1.0;
      case "4:5":
        return 4 / 5;
      case "16:9":
        return 16 / 9;
      case "free":
      default:
        return null;
    }
  };

  const handlePointerDown = (
    type: DragType,
    e: React.PointerEvent<HTMLDivElement>
  ) => {
    e.preventDefault();
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    activeDragRef.current = {
      type,
      startX: e.clientX,
      startY: e.clientY,
      startCrop: { ...cropBox },
    };
  };

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!activeDragRef.current || !containerRef.current) return;
      const { type, startX, startY, startCrop } = activeDragRef.current;

      const rect = containerRef.current.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;

      const scaleX = videoWidth / rect.width;
      const scaleY = videoHeight / rect.height;

      const deltaX = (e.clientX - startX) * scaleX;
      const deltaY = (e.clientY - startY) * scaleY;

      const ratio = getTargetRatio(aspectRatio);
      let { x, y, width, height } = startCrop;

      const minSize = Math.max(30, Math.min(videoWidth, videoHeight) * 0.1);

      if (type === "move") {
        x = Math.max(0, Math.min(videoWidth - width, startCrop.x + deltaX));
        y = Math.max(0, Math.min(videoHeight - height, startCrop.y + deltaY));
      } else {
        // Resizing
        if (ratio !== null) {
          // Locked aspect ratio
          if (type === "se") {
            const rawW = startCrop.width + deltaX;
            const rawH = startCrop.height + deltaY;
            const chosenW = Math.max(
              minSize,
              Math.min(videoWidth - startCrop.x, (rawW + rawH * ratio) / 2)
            );
            width = chosenW;
            height = chosenW / ratio;
            if (startCrop.y + height > videoHeight) {
              height = videoHeight - startCrop.y;
              width = height * ratio;
            }
          } else if (type === "nw") {
            const maxDeltaX = startCrop.width - minSize;
            const maxDeltaY = startCrop.height - minSize;
            let dX = Math.min(maxDeltaX, Math.max(-startCrop.x, deltaX));
            let dY = Math.min(maxDeltaY, Math.max(-startCrop.y, deltaY));
            const avgD = (dX + dY * ratio) / 2;
            dX = avgD;
            dY = avgD / ratio;
            x = startCrop.x + dX;
            y = startCrop.y + dY;
            width = startCrop.width - dX;
            height = startCrop.height - dY;
          } else if (type === "ne") {
            const rawW = Math.max(
              minSize,
              Math.min(videoWidth - startCrop.x, startCrop.width + deltaX)
            );
            width = rawW;
            height = rawW / ratio;
            y = startCrop.y + (startCrop.height - height);
            if (y < 0) {
              y = 0;
              height = startCrop.y + startCrop.height;
              width = height * ratio;
            }
          } else if (type === "sw") {
            const rawW = Math.max(
              minSize,
              Math.min(startCrop.x + startCrop.width, startCrop.width - deltaX)
            );
            width = rawW;
            height = rawW / ratio;
            x = startCrop.x + (startCrop.width - width);
            if (startCrop.y + height > videoHeight) {
              height = videoHeight - startCrop.y;
              width = height * ratio;
              x = startCrop.x + (startCrop.width - width);
            }
          } else if (type === "e" || type === "w") {
            const sign = type === "e" ? 1 : -1;
            const newW = Math.max(minSize, startCrop.width + sign * deltaX);
            const newH = newW / ratio;
            if (type === "w") {
              const newX = startCrop.x + (startCrop.width - newW);
              if (newX >= 0) {
                x = newX;
                width = newW;
              }
            } else {
              if (startCrop.x + newW <= videoWidth) {
                width = newW;
              }
            }
            if (startCrop.y + newH <= videoHeight) {
              height = newH;
            }
          } else if (type === "s" || type === "n") {
            const sign = type === "s" ? 1 : -1;
            const newH = Math.max(minSize, startCrop.height + sign * deltaY);
            const newW = newH * ratio;
            if (type === "n") {
              const newY = startCrop.y + (startCrop.height - newH);
              if (newY >= 0) {
                y = newY;
                height = newH;
              }
            } else {
              if (startCrop.y + newH <= videoHeight) {
                height = newH;
              }
            }
            if (startCrop.x + newW <= videoWidth) {
              width = newW;
            }
          }
        } else {
          // Free aspect ratio
          if (type.includes("e")) {
            width = Math.max(
              minSize,
              Math.min(videoWidth - startCrop.x, startCrop.width + deltaX)
            );
          }
          if (type.includes("s")) {
            height = Math.max(
              minSize,
              Math.min(videoHeight - startCrop.y, startCrop.height + deltaY)
            );
          }
          if (type.includes("w")) {
            const newX = Math.max(
              0,
              Math.min(startCrop.x + startCrop.width - minSize, startCrop.x + deltaX)
            );
            width = startCrop.x + startCrop.width - newX;
            x = newX;
          }
          if (type.includes("n")) {
            const newY = Math.max(
              0,
              Math.min(startCrop.y + startCrop.height - minSize, startCrop.y + deltaY)
            );
            height = startCrop.y + startCrop.height - newY;
            y = newY;
          }
        }
      }

      // Final boundary clamp
      x = Math.max(0, Math.min(videoWidth - minSize, x));
      y = Math.max(0, Math.min(videoHeight - minSize, y));
      width = Math.max(minSize, Math.min(videoWidth - x, width));
      height = Math.max(minSize, Math.min(videoHeight - y, height));

      onChange({
        x: Math.round(x),
        y: Math.round(y),
        width: Math.round(width),
        height: Math.round(height),
      });
    },
    [aspectRatio, onChange, videoHeight, videoWidth]
  );

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (activeDragRef.current) {
      try {
        (e.target as HTMLElement).releasePointerCapture(e.pointerId);
      } catch {
        // Safe fallback
      }
      activeDragRef.current = null;
    }
  };

  // Preset button actions
  const handleCenter = () => {
    const newX = Math.round((videoWidth - cropBox.width) / 2);
    const newY = Math.round((videoHeight - cropBox.height) / 2);
    onChange({
      ...cropBox,
      x: Math.max(0, newX),
      y: Math.max(0, newY),
    });
  };

  const handleFitMax = () => {
    const ratio = getTargetRatio(aspectRatio) ?? 1.0;
    let w = videoWidth;
    let h = w / ratio;
    if (h > videoHeight) {
      h = videoHeight;
      w = h * ratio;
    }
    const x = Math.round((videoWidth - w) / 2);
    const y = Math.round((videoHeight - h) / 2);
    onChange({
      x: Math.max(0, x),
      y: Math.max(0, y),
      width: Math.round(w),
      height: Math.round(h),
    });
  };

  const handleResetSquare = () => {
    onAspectRatioChange("1:1");
    const side = Math.min(videoWidth, videoHeight);
    const x = Math.round((videoWidth - side) / 2);
    const y = Math.round((videoHeight - side) / 2);
    onChange({
      x,
      y,
      width: side,
      height: side,
    });
  };

  // Convert pixel crop box to percentage for CSS placement
  const leftPct = (cropBox.x / videoWidth) * 100;
  const topPct = (cropBox.y / videoHeight) * 100;
  const widthPct = (cropBox.width / videoWidth) * 100;
  const heightPct = (cropBox.height / videoHeight) * 100;

  return (
    <div className="space-y-2 select-none w-full">
      {/* Top Toolbar: Aspect Ratio Selector & Presets */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs bg-muted/40 p-2 rounded-lg border border-border/50">
        <div className="flex items-center gap-1.5">
          <span className="text-muted-foreground font-medium text-[11px]">
            Aspect Ratio:
          </span>
          {(["1:1", "free", "4:5", "16:9"] as AspectRatioMode[]).map((mode) => (
            <Button
              key={mode}
              type="button"
              variant={aspectRatio === mode ? "default" : "outline"}
              size="sm"
              onClick={() => {
                onAspectRatioChange(mode);
                if (mode === "1:1") {
                  const side = Math.min(cropBox.width, cropBox.height);
                  onChange({ ...cropBox, width: side, height: side });
                }
              }}
              className="h-6 px-2 text-[11px]"
            >
              {mode === "1:1" ? "1:1 Square" : mode === "free" ? "Free" : mode}
            </Button>
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleCenter}
            className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground"
            title="Center crop box"
          >
            <Crosshair className="h-3 w-3 mr-1" /> Center
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleFitMax}
            className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground"
            title="Fit to maximum size"
          >
            <Maximize2 className="h-3 w-3 mr-1" /> Max
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleResetSquare}
            className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground"
            title="Reset crop to centered square"
          >
            <RotateCcw className="h-3 w-3 mr-1" /> Reset
          </Button>
        </div>
      </div>

      {/* Video Content & Interactive Overlay Wrapper */}
      <div className="flex justify-center items-center w-full">
        <div
          ref={containerRef}
          className="relative inline-block overflow-hidden max-w-full rounded-lg bg-black"
        >
          {children}

          {/* Dimmed Exterior: Top */}
          <div
            className="absolute top-0 left-0 right-0 bg-black/60 pointer-events-none transition-opacity"
            style={{ height: `${topPct}%` }}
          />

          {/* Dimmed Exterior: Bottom */}
          <div
            className="absolute bottom-0 left-0 right-0 bg-black/60 pointer-events-none transition-opacity"
            style={{ height: `${100 - (topPct + heightPct)}%` }}
          />

          {/* Dimmed Exterior: Left */}
          <div
            className="absolute left-0 bg-black/60 pointer-events-none transition-opacity"
            style={{
              top: `${topPct}%`,
              height: `${heightPct}%`,
              width: `${leftPct}%`,
            }}
          />

          {/* Dimmed Exterior: Right */}
          <div
            className="absolute right-0 bg-black/60 pointer-events-none transition-opacity"
            style={{
              top: `${topPct}%`,
              height: `${heightPct}%`,
              width: `${100 - (leftPct + widthPct)}%`,
            }}
          />

          {/* The Active Crop Window */}
          <div
            onPointerDown={(e) => handlePointerDown("move", e)}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            className="absolute border-2 border-amber-400 cursor-move shadow-[0_0_12px_rgba(251,191,36,0.35)] transition-colors active:border-amber-300 z-20 touch-none"
            style={{
              left: `${leftPct}%`,
              top: `${topPct}%`,
              width: `${widthPct}%`,
              height: `${heightPct}%`,
            }}
          >
            {/* Rule-of-Thirds Grid */}
            <div className="absolute inset-0 grid grid-cols-3 grid-rows-3 pointer-events-none">
              <div className="border-r border-b border-amber-400/25" />
              <div className="border-r border-b border-amber-400/25" />
              <div className="border-b border-amber-400/25" />
              <div className="border-r border-b border-amber-400/25" />
              <div className="border-r border-b border-amber-400/25" />
              <div className="border-b border-amber-400/25" />
              <div className="border-r border-amber-400/25" />
              <div className="border-r border-amber-400/25" />
              <div />
            </div>

            {/* Dimension Badge */}
            <div className="absolute -top-6 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded bg-black/85 border border-amber-400/40 text-[10px] font-mono text-amber-300 shadow pointer-events-none whitespace-nowrap">
              {cropBox.width} × {cropBox.height} px
            </div>

            {/* 4 Corner Resize Handles */}
            <div
              onPointerDown={(e) => handlePointerDown("nw", e)}
              className="absolute -top-1.5 -left-1.5 w-3.5 h-3.5 bg-amber-400 border border-black/80 rounded-sm cursor-nwse-resize shadow active:scale-125 z-30"
            />
            <div
              onPointerDown={(e) => handlePointerDown("ne", e)}
              className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 bg-amber-400 border border-black/80 rounded-sm cursor-nesw-resize shadow active:scale-125 z-30"
            />
            <div
              onPointerDown={(e) => handlePointerDown("sw", e)}
              className="absolute -bottom-1.5 -left-1.5 w-3.5 h-3.5 bg-amber-400 border border-black/80 rounded-sm cursor-nesw-resize shadow active:scale-125 z-30"
            />
            <div
              onPointerDown={(e) => handlePointerDown("se", e)}
              className="absolute -bottom-1.5 -right-1.5 w-3.5 h-3.5 bg-amber-400 border border-black/80 rounded-sm cursor-nwse-resize shadow active:scale-125 z-30"
            />

            {/* 4 Edge Resize Handles */}
            <div
              onPointerDown={(e) => handlePointerDown("n", e)}
              className="absolute -top-1 left-1/2 -translate-x-1/2 w-6 h-2 bg-amber-400/80 hover:bg-amber-400 border border-black/60 rounded-full cursor-ns-resize z-20"
            />
            <div
              onPointerDown={(e) => handlePointerDown("s", e)}
              className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-6 h-2 bg-amber-400/80 hover:bg-amber-400 border border-black/60 rounded-full cursor-ns-resize z-20"
            />
            <div
              onPointerDown={(e) => handlePointerDown("w", e)}
              className="absolute -left-1 top-1/2 -translate-y-1/2 h-6 w-2 bg-amber-400/80 hover:bg-amber-400 border border-black/60 rounded-full cursor-ew-resize z-20"
            />
            <div
              onPointerDown={(e) => handlePointerDown("e", e)}
              className="absolute -right-1 top-1/2 -translate-y-1/2 h-6 w-2 bg-amber-400/80 hover:bg-amber-400 border border-black/60 rounded-full cursor-ew-resize z-20"
            />
          </div>
        </div>
      </div>

      {/* Footer live coordinate feedback */}
      <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground px-1">
        <span>
          Position: X: {cropBox.x}, Y: {cropBox.y}
        </span>
        <Badge
          variant="outline"
          className="text-[10px] font-mono text-amber-400 border-amber-400/30"
        >
          Selected Box: {cropBox.width}×{cropBox.height}
        </Badge>
        <span>
          Video: {videoWidth}×{videoHeight}
        </span>
      </div>
    </div>
  );
}
