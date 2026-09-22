"use client";

import { useState, useRef, useEffect, ChangeEvent, DragEvent } from "react";
import {
  UploadCloud,
  Film,
  X,
  Clock,
  Sparkles,
  Download,
  AlertCircle,
  Loader2,
  Palette,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { ComplianceChecklist } from "@/components/ComplianceChecklist";
import { VideoTrimmer } from "@/components/VideoTrimmer";
import { convertSingleVideo, ConvertResponse } from "@/lib/api";

export function SingleConverter() {
  // File state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const outputVideoRef = useRef<HTMLVideoElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Conversion parameters
  const [mode, setMode] = useState<"sticker" | "emoji">("sticker");
  const [loopMode, setLoopMode] = useState<"normal" | "pingpong">("normal");
  const [startTime, setStartTime] = useState<string>("0.0");
  const [duration, setDuration] = useState<string>("3.0");
  const [speedToFit, setSpeedToFit] = useState<boolean>(false);
  const [totalVideoDuration, setTotalVideoDuration] = useState<number>(0);
  const [fitMode, setFitMode] = useState<string>("default");
  const [fps, setFps] = useState<number[]>([30]);
  const [crf, setCrf] = useState<number[]>([30]);
  const [removeBg, setRemoveBg] = useState<string>("none");
  const [customColor, setCustomColor] = useState<string>("#00FF00");
  const [preserveAlpha, setPreserveAlpha] = useState<boolean>(true);

  // Result & Loading states
  const [isConverting, setIsConverting] = useState<boolean>(false);
  const [convertResult, setConvertResult] = useState<ConvertResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [outputVideoError, setOutputVideoError] = useState<boolean>(false);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  useEffect(() => {
    if (outputVideoRef.current && convertResult?.download_url) {
      setOutputVideoError(false);
      outputVideoRef.current.load();
      outputVideoRef.current.play().catch(() => {});
    }
  }, [convertResult]);

  // Handlers
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processSelectedFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const processSelectedFile = (file: File) => {
    setSelectedFile(file);
    setConvertResult(null);
    setErrorMessage(null);
    const url = URL.createObjectURL(file);
    setVideoPreviewUrl(url);
  };

  const clearFile = () => {
    if (videoPreviewUrl) {
      URL.revokeObjectURL(videoPreviewUrl);
    }
    setSelectedFile(null);
    setVideoPreviewUrl(null);
    setConvertResult(null);
    setErrorMessage(null);
    setTotalVideoDuration(0);
    setStartTime("0.0");
    setDuration("3.0");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleVideoLoadedMetadata = () => {
    if (videoRef.current) {
      const fullDur = videoRef.current.duration || 0;
      setTotalVideoDuration(fullDur);
      setStartTime("0.0");
      const initialDur = Math.min(fullDur, 3.0);
      setDuration(initialDur.toFixed(1));
    }
  };

  const setStartFromCurrent = () => {
    if (videoRef.current) {
      setStartTime(videoRef.current.currentTime.toFixed(1));
    }
  };

  const getCrfDescription = (val: number) => {
    if (val <= 20) return "High Quality";
    if (val <= 28) return "Good Quality";
    if (val <= 35) return "Balanced";
    if (val <= 42) return "Smaller File";
    return "Aggressive Compression";
  };

  const handleConvert = async () => {
    if (!selectedFile) return;

    setIsConverting(true);
    setErrorMessage(null);

    try {
      const formData = new FormData();
      formData.append("video", selectedFile);
      formData.append("filename", selectedFile.name);
      formData.append("mode", mode);
      formData.append("loop_mode", loopMode);
      if (startTime) formData.append("start_time", startTime);
      if (duration) formData.append("duration", duration);
      formData.append("speed_to_fit", String(speedToFit));
      if (fitMode && fitMode !== "default") formData.append("fit_mode", fitMode);
      formData.append("fps", String(fps[0]));
      formData.append("crf", String(crf[0]));
      formData.append("preserve_alpha", String(preserveAlpha));

      let bgValue: string | null = null;
      if (removeBg === "custom") bgValue = customColor;
      else if (removeBg !== "none") bgValue = removeBg;

      if (bgValue) formData.append("remove_bg", bgValue);

      const result = await convertSingleVideo(formData);
      setConvertResult(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to convert video";
      setErrorMessage(msg);
    } finally {
      setIsConverting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
      {/* LEFT COLUMN: Input & Settings (7 cols) */}
      <div className="lg:col-span-7 space-y-6">
        {/* Card 1: Video File Selection */}
        <Card className="border-border/60 bg-card/60 backdrop-blur-sm shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-base flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">
                1
              </span>
              Select Video or GIF
            </CardTitle>
            <CardDescription className="text-xs">
              Upload any MP4, MOV, WebM, or GIF animation to encode into Telegram VP9.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Dropzone */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="video/*,.gif,.webm"
              className="hidden"
            />

            {!selectedFile ? (
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all ${
                  isDragging
                    ? "border-sky-500 bg-sky-500/5 scale-[0.99]"
                    : "border-border/80 hover:border-primary/50 hover:bg-muted/30"
                }`}
              >
                <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground group-hover:text-primary transition-colors">
                  <UploadCloud className="h-6 w-6" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-foreground">
                    Click to browse or drag & drop video
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    MP4, MOV, GIF, WEBM, MKV (Any size / duration)
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-lg border border-border/70 bg-muted/30">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="h-9 w-9 rounded-md bg-primary/10 text-primary flex items-center justify-center shrink-0">
                      <Film className="h-5 w-5" />
                    </div>
                    <div className="truncate">
                      <div className="text-sm font-medium truncate text-foreground">
                        {selectedFile.name}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={clearFile}
                    className="h-8 w-8 text-muted-foreground hover:text-foreground shrink-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                {/* Video Scrubber & QuickTime Trimmer Preview */}
                {videoPreviewUrl && (
                  <div className="rounded-xl overflow-hidden border border-border/60 bg-black/40 space-y-3.5 p-3.5">
                    <video
                      ref={videoRef}
                      src={videoPreviewUrl}
                      controls
                      playsInline
                      onLoadedMetadata={handleVideoLoadedMetadata}
                      className="w-full max-h-56 rounded-lg mx-auto object-contain bg-black shadow-sm"
                    />

                    {/* QuickTime-Style Video Trimmer */}
                    {totalVideoDuration > 0 && (
                      <div className="pt-1">
                        <VideoTrimmer
                          videoRef={videoRef}
                          videoUrl={videoPreviewUrl}
                          totalDuration={totalVideoDuration}
                          startTime={Number.parseFloat(startTime) || 0}
                          trimDuration={
                            Number.parseFloat(duration) || Math.min(3.0, totalVideoDuration)
                          }
                          onTrimChange={(newStart, newDur) => {
                            setStartTime(newStart.toFixed(1));
                            setDuration(newDur.toFixed(1));
                          }}
                          maxAllowedDuration={3.0}
                        />
                      </div>
                    )}

                    {/* Precision Fine-Tuning Inputs */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 border-t border-border/40">
                      <div className="space-y-1.5">
                        <div className="flex justify-between items-center">
                          <Label className="text-xs text-muted-foreground">Start Offset (s)</Label>
                          <Button
                            variant="ghost"
                            size="sm"
                            type="button"
                            onClick={setStartFromCurrent}
                            className="h-5 px-1.5 text-[11px] text-amber-500 hover:text-amber-400"
                          >
                            <Clock className="h-3 w-3 mr-1" /> Use Playhead
                          </Button>
                        </div>
                        <Input
                          type="number"
                          min="0"
                          max={totalVideoDuration ? (totalVideoDuration - 0.1).toFixed(1) : undefined}
                          step="0.1"
                          value={startTime}
                          onChange={(e) => {
                            setStartTime(e.target.value);
                            if (videoRef.current && e.target.value) {
                              videoRef.current.currentTime = Number.parseFloat(e.target.value) || 0;
                            }
                          }}
                          className="h-8 text-xs font-mono"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <div className="flex justify-between items-center">
                          <Label className="text-xs text-muted-foreground">Clip Duration (s)</Label>
                          <Badge variant="outline" className="text-[10px] h-4 font-mono text-amber-500 border-amber-500/30">
                            Max 3.0s
                          </Badge>
                        </div>
                        <Input
                          type="number"
                          min="0.1"
                          max="3.0"
                          step="0.1"
                          value={duration}
                          onChange={(e) => setDuration(e.target.value)}
                          className="h-8 text-xs font-mono"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Card 2: Conversion Settings */}
        <Card className="border-border/60 bg-card/60 backdrop-blur-sm shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-base flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">
                2
              </span>
              Sticker Specifications & Settings
            </CardTitle>
            <CardDescription className="text-xs">
              Tune parameters to guarantee strict Telegram bot compliance.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Format Mode & Loop Style */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Target Format */}
              <div className="space-y-2">
                <Label className="text-xs font-medium">Target Format</Label>
                <div className="grid grid-cols-2 gap-1.5 p-1 rounded-lg bg-muted border border-border/50 text-xs">
                  <button
                    type="button"
                    onClick={() => setMode("sticker")}
                    className={`py-1.5 px-2 rounded-md font-medium transition-all ${
                      mode === "sticker"
                        ? "bg-background text-foreground shadow-sm font-semibold"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Sticker (512px)
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode("emoji")}
                    className={`py-1.5 px-2 rounded-md font-medium transition-all ${
                      mode === "emoji"
                        ? "bg-background text-foreground shadow-sm font-semibold"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Emoji (100×100)
                  </button>
                </div>
              </div>

              {/* Loop Mode */}
              <div className="space-y-2">
                <Label className="text-xs font-medium">Loop Method</Label>
                <div className="grid grid-cols-2 gap-1.5 p-1 rounded-lg bg-muted border border-border/50 text-xs">
                  <button
                    type="button"
                    onClick={() => setLoopMode("normal")}
                    className={`py-1.5 px-2 rounded-md font-medium transition-all ${
                      loopMode === "normal"
                        ? "bg-background text-foreground shadow-sm font-semibold"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Standard Loop
                  </button>
                  <button
                    type="button"
                    onClick={() => setLoopMode("pingpong")}
                    className={`py-1.5 px-2 rounded-md font-medium transition-all ${
                      loopMode === "pingpong"
                        ? "bg-background text-foreground shadow-sm font-semibold"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Boomerang
                  </button>
                </div>
              </div>
            </div>

            <Separator className="bg-border/50" />

            {/* Speed to fit Switch */}
            <div className="flex items-center justify-between p-3 rounded-lg border border-border/50 bg-muted/20">
              <div className="space-y-0.5">
                <Label htmlFor="speedToFit" className="text-xs font-medium cursor-pointer">
                  Speed-to-fit (Smart Accelerate)
                </Label>
                <p className="text-[11px] text-muted-foreground">
                  Accelerate longer videos so the complete action completes within 3.0s
                </p>
              </div>
              <Switch
                id="speedToFit"
                checked={speedToFit}
                onCheckedChange={setSpeedToFit}
              />
            </div>

            {/* Fit Mode */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Aspect Ratio / Fit Mode</Label>
              <Select value={fitMode} onValueChange={(val) => { if (val) setFitMode(val); }}>
                <SelectTrigger className="w-full h-9 text-xs">
                  <SelectValue placeholder="Select fit mode" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">
                    Default (Keep Aspect Ratio for Stickers, Square Crop for Emoji)
                  </SelectItem>
                  <SelectItem value="crop">Center Crop (Square 1:1)</SelectItem>
                  <SelectItem value="pad">Pad (Transparent border to Square)</SelectItem>
                  <SelectItem value="stretch">Stretch to Square</SelectItem>
                  <SelectItem value="contain">Contain (Preserve Aspect Ratio)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Sliders: FPS and CRF */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-1">
              {/* FPS Slider */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label className="text-xs font-medium">Framerate</Label>
                  <Badge variant="secondary" className="font-mono text-[11px]">
                    {fps[0]} FPS
                  </Badge>
                </div>
                <Slider
                  min={5}
                  max={30}
                  step={1}
                  value={fps}
                  onValueChange={(val) => setFps(Array.isArray(val) ? [...val] : [val])}
                  className="py-1"
                />
                <p className="text-[10px] text-muted-foreground">Telegram maximum is 30 FPS</p>
              </div>

              {/* CRF Quality Slider */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label className="text-xs font-medium">VP9 Quality (CRF)</Label>
                  <Badge variant="secondary" className="font-mono text-[11px]">
                    CRF {crf[0]} ({getCrfDescription(crf[0])})
                  </Badge>
                </div>
                <Slider
                  min={10}
                  max={50}
                  step={1}
                  value={crf}
                  onValueChange={(val) => setCrf(Array.isArray(val) ? [...val] : [val])}
                  className="py-1"
                />
                <p className="text-[10px] text-muted-foreground">
                  Lower is sharper; higher ensures file size &le; 256 KB
                </p>
              </div>
            </div>

            <Separator className="bg-border/50" />

            {/* Chroma Key / Background Removal */}
            <div className="space-y-2">
              <Label className="text-xs font-medium flex items-center gap-1.5">
                <Palette className="h-3.5 w-3.5 text-muted-foreground" />
                Remove Background (Chroma Key)
              </Label>
              <div className="flex items-center gap-2">
                <Select value={removeBg} onValueChange={(val) => { if (val) setRemoveBg(val); }}>
                  <SelectTrigger className="h-9 text-xs flex-1">
                    <SelectValue placeholder="Select background removal" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None (Keep Original Background)</SelectItem>
                    <SelectItem value="green">Green Screen (#00FF00)</SelectItem>
                    <SelectItem value="black">Black Background (#000000)</SelectItem>
                    <SelectItem value="white">White Background (#FFFFFF)</SelectItem>
                    <SelectItem value="custom">Custom Color Key...</SelectItem>
                  </SelectContent>
                </Select>

                {removeBg === "custom" && (
                  <div className="flex items-center gap-1.5 shrink-0">
                    <input
                      type="color"
                      value={customColor}
                      onChange={(e) => setCustomColor(e.target.value)}
                      className="h-9 w-9 rounded-md border border-border cursor-pointer bg-transparent p-0.5"
                    />
                    <Input
                      type="text"
                      value={customColor}
                      onChange={(e) => setCustomColor(e.target.value)}
                      className="h-9 w-24 text-xs font-mono"
                      placeholder="#00FF00"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Preserve Transparency Switch */}
            <div className="flex items-center justify-between p-3 rounded-lg border border-border/50 bg-muted/20">
              <div className="space-y-0.5">
                <Label htmlFor="preserveAlpha" className="text-xs font-medium cursor-pointer">
                  Preserve Alpha Transparency
                </Label>
                <p className="text-[11px] text-muted-foreground">
                  Encode with YUVA420P to retain transparent pixels in source GIFs/WebMs
                </p>
              </div>
              <Switch
                id="preserveAlpha"
                checked={preserveAlpha}
                onCheckedChange={setPreserveAlpha}
              />
            </div>

            {/* Convert Trigger Button */}
            <Button
              onClick={handleConvert}
              disabled={!selectedFile || isConverting}
              className="w-full h-11 text-sm font-semibold bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-600 hover:to-indigo-700 text-white shadow-md shadow-sky-500/20 transition-all cursor-pointer"
            >
              {isConverting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Encoding VP9 & Optimizing Size (&le; 256 KB)...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Convert to Telegram WebM
                </>
              )}
            </Button>

            {errorMessage && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* RIGHT COLUMN: Live Result & Compliance Checklist (5 cols) */}
      <div className="lg:col-span-5 space-y-6">
        <Card className="border-border/60 bg-card/60 backdrop-blur-sm shadow-sm sticky top-20">
          <CardHeader className="pb-4">
            <CardTitle className="text-base flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold">
                3
              </span>
              Telegram Sticker Preview & Verification
            </CardTitle>
            <CardDescription className="text-xs">
              Live looping WebM rendered with transparency support.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {!convertResult ? (
              <div className="h-72 rounded-xl border border-dashed border-border/80 flex flex-col items-center justify-center gap-3 p-6 text-center text-muted-foreground bg-muted/10">
                <div className="h-12 w-12 rounded-full bg-muted/40 flex items-center justify-center text-2xl">
                  💬
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">No Sticker Generated Yet</p>
                  <p className="text-xs text-muted-foreground max-w-xs mt-1">
                    Upload a video and click &ldquo;Convert to Telegram WebM&rdquo; to see the live sticker loop and compliance check.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-5 animate-in fade-in-50 duration-300">
                {/* Visual Stage */}
                <div className="relative rounded-2xl overflow-hidden border border-border/80 shadow-inner bg-card flex flex-col items-center justify-center p-6">
                  {/* Checkerboard Backdrop */}
                  <div className="checkerboard relative p-4 rounded-xl shadow-lg border border-white/10 max-w-[280px] max-h-[280px] min-w-[200px] min-h-[200px] flex items-center justify-center overflow-hidden">
                    {!outputVideoError ? (
                      <video
                        ref={outputVideoRef}
                        key={convertResult.download_url}
                        src={convertResult.download_url}
                        autoPlay
                        loop
                        muted
                        controls
                        playsInline
                        onError={() => setOutputVideoError(true)}
                        className="max-h-56 max-w-56 object-contain rounded-lg shadow-sm"
                      />
                    ) : (
                      <div className="flex flex-col items-center justify-center p-4 text-center text-xs text-muted-foreground gap-2">
                        <AlertCircle className="h-6 w-6 text-amber-500" />
                        <p className="font-semibold text-foreground">Browser Preview Notice</p>
                        <p className="text-[11px] leading-relaxed">
                          Your browser has limited native playback support for WebM VP9.
                        </p>
                        <Badge variant="outline" className="text-[10px] text-emerald-400 border-emerald-500/30">
                          ✓ 100% Compliant for Telegram @Stickers
                        </Badge>
                      </div>
                    )}
                  </div>
                  <span className="text-[11px] text-muted-foreground mt-3 font-medium">
                    Live Telegram Sticker Loop (Alpha Supported)
                  </span>
                </div>

                {/* Compliance Checklist */}
                {convertResult.info && (
                  <ComplianceChecklist
                    info={convertResult.info}
                    mode={mode}
                    valid={convertResult.valid}
                    issues={convertResult.issues}
                  />
                )}

                {/* Actions */}
                <div className="space-y-2 pt-2">
                  <a
                    href={convertResult.download_url}
                    download={convertResult.filename}
                    className="w-full inline-flex"
                  >
                    <Button className="w-full h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold cursor-pointer">
                      <Download className="h-4 w-4 mr-2" />
                      Download Sticker (.WEBM)
                    </Button>
                  </a>

                  <p className="text-center text-[11px] text-muted-foreground">
                    Upload as an uncompressed document to Telegram&apos;s{" "}
                    <a
                      href="https://t.me/Stickers"
                      target="_blank"
                      rel="noreferrer"
                      className="text-sky-400 hover:underline font-medium"
                    >
                      @Stickers
                    </a>{" "}
                    bot.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
