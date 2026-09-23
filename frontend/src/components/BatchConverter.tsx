"use client";

import { useEffect, useState } from "react";
import {
  FolderOpen,
  FolderInput,
  FolderOutput,
  RefreshCw,
  Film,
  Zap,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { fetchFolders, runBatchProcess, FolderResponse, BatchResponse } from "@/lib/api";

export function BatchConverter() {
  const [folders, setFolders] = useState<FolderResponse | null>(null);
  const [isLoadingFolders, setIsLoadingFolders] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [batchResult, setBatchResult] = useState<BatchResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Settings
  const [mode, setMode] = useState<string>("sticker");
  const [fitMode, setFitMode] = useState<string>("default");
  const [duration, setDuration] = useState<string>("3.0");
  const [fps, setFps] = useState<string>("30");
  const [crf, setCrf] = useState<string>("30");
  const [removeBg, setRemoveBg] = useState<string>("none");
  const [speedToFit, setSpeedToFit] = useState<boolean>(false);
  const [boomerang, setBoomerang] = useState<boolean>(false);
  const [preserveAlpha, setPreserveAlpha] = useState<boolean>(true);
  const [overwrite, setOverwrite] = useState<boolean>(false);
  const [recursive, setRecursive] = useState<boolean>(false);

  const loadFolders = async () => {
    setIsLoadingFolders(true);
    setErrorMessage(null);
    try {
      const data = await fetchFolders();
      setFolders(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load folders";
      setErrorMessage(msg);
    } finally {
      setIsLoadingFolders(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    fetchFolders()
      .then((data) => {
        if (isMounted) setFolders(data);
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load folders";
          setErrorMessage(msg);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleRunBatch = async () => {
    setIsProcessing(true);
    setErrorMessage(null);
    setBatchResult(null);

    const toastId = toast.loading("Processing batch...", {
      description: `Converting ${folders?.input_files.length ?? 0} videos with VP9 engine`,
    });

    try {
      const result = await runBatchProcess({
        mode,
        duration: duration ? parseFloat(duration) : undefined,
        fit_mode: fitMode !== "default" ? fitMode : undefined,
        fps: parseInt(fps, 10),
        crf: parseInt(crf, 10),
        remove_bg: removeBg !== "none" ? removeBg : undefined,
        speed_to_fit: speedToFit,
        loop_mode: boomerang ? "pingpong" : "normal",
        preserve_alpha: preserveAlpha,
        overwrite,
        recursive,
      });

      setBatchResult(result);
      await loadFolders();

      if (result.failed === 0) {
        toast.success("Batch Completed!", {
          id: toastId,
          description: `Successfully converted ${result.succeeded} stickers (${result.skipped} skipped).`,
        });
      } else {
        toast.warning("Batch Finished with Issues", {
          id: toastId,
          description: `${result.succeeded} succeeded, ${result.failed} failed, ${result.skipped} skipped.`,
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Batch processing failed";
      setErrorMessage(msg);
      toast.error("Batch Failed", {
        id: toastId,
        description: msg,
      });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Folder Inspection Section */}
      <Card className="border-border/60 bg-card/60 backdrop-blur-sm shadow-sm">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle className="text-base flex items-center gap-2">
                <FolderOpen className="h-5 w-5 text-sky-400" />
                Folder Batch Processing
              </CardTitle>
              <CardDescription className="text-xs">
                Drop multiple videos into <code>input_videos/</code> and convert them all into Telegram-compliant WebM stickers in <code>output_stickers/</code>.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadFolders}
              disabled={isLoadingFolders}
              className="h-8 text-xs cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${isLoadingFolders ? "animate-spin" : ""}`} />
              Refresh Folders
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Input Column */}
            <div className="rounded-xl border border-border/70 bg-muted/20 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FolderInput className="h-4 w-4 text-sky-400" />
                  <span className="text-xs font-semibold text-foreground">
                    Input Videos
                  </span>
                </div>
                <Badge variant="secondary" className="font-mono text-xs">
                  {folders?.input_files.length ?? 0} files
                </Badge>
              </div>
              <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                {folders?.input_files.length ? (
                  folders.input_files.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 p-2 rounded-lg bg-card/80 border border-border/40 text-xs font-mono truncate"
                    >
                      <Film className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <span className="truncate">{file}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground py-6 text-center italic">
                    No videos found in input_videos/
                  </p>
                )}
              </div>
            </div>

            {/* Output Column */}
            <div className="rounded-xl border border-border/70 bg-muted/20 p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FolderOutput className="h-4 w-4 text-emerald-400" />
                  <span className="text-xs font-semibold text-foreground">
                    Converted Stickers
                  </span>
                </div>
                <Badge variant="secondary" className="font-mono text-xs">
                  {folders?.output_files.length ?? 0} stickers
                </Badge>
              </div>
              <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                {folders?.output_files.length ? (
                  folders.output_files.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 p-2 rounded-lg bg-card/80 border border-border/40 text-xs font-mono truncate text-emerald-400"
                    >
                      <Zap className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">{file}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground py-6 text-center italic">
                    No stickers generated yet in output_stickers/
                  </p>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Batch Settings & Execution */}
      <Card className="border-border/60 bg-card/60 backdrop-blur-sm shadow-sm">
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Batch Configuration Options</CardTitle>
          <CardDescription className="text-xs">
            Global settings applied uniformly to all input videos during conversion.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {/* Mode */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Target Mode</Label>
              <Select value={mode} onValueChange={(val) => { if (val) setMode(val); }}>
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sticker">Stickers (512px max edge)</SelectItem>
                  <SelectItem value="emoji">Custom Emoji (100×100 square)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Fit mode */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Fit / Aspect Ratio</Label>
              <Select value={fitMode} onValueChange={(val) => { if (val) setFitMode(val); }}>
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">Default Fit</SelectItem>
                  <SelectItem value="crop">Center Crop (1:1)</SelectItem>
                  <SelectItem value="pad">Pad (Transparent)</SelectItem>
                  <SelectItem value="stretch">Stretch</SelectItem>
                  <SelectItem value="contain">Contain (Preserve AR)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Duration */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Max Duration (s)</Label>
              <Input
                type="number"
                min="0.5"
                max="3.0"
                step="0.1"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className="h-9 text-xs font-mono"
              />
            </div>

            {/* FPS */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Framerate</Label>
              <Select value={fps} onValueChange={(val) => { if (val) setFps(val); }}>
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">30 FPS (Max standard)</SelectItem>
                  <SelectItem value="25">25 FPS</SelectItem>
                  <SelectItem value="20">20 FPS</SelectItem>
                  <SelectItem value="15">15 FPS</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Quality CRF */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">VP9 Quality (CRF)</Label>
              <Select value={crf} onValueChange={(val) => { if (val) setCrf(val); }}>
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="20">CRF 20 (High Quality)</SelectItem>
                  <SelectItem value="30">CRF 30 (Balanced / Default)</SelectItem>
                  <SelectItem value="38">CRF 38 (Smaller File)</SelectItem>
                  <SelectItem value="45">CRF 45 (Aggressive Compression)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Remove BG */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Chroma-Key Background</Label>
              <Select value={removeBg} onValueChange={(val) => { if (val) setRemoveBg(val); }}>
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None (Keep Original)</SelectItem>
                  <SelectItem value="green">Green Screen (#00FF00)</SelectItem>
                  <SelectItem value="black">Black Background</SelectItem>
                  <SelectItem value="white">White Background</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Separator className="bg-border/50" />

          {/* Toggle Switches */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            <div className="flex items-center justify-between p-2.5 rounded-lg border border-border/40 bg-muted/20">
              <Label htmlFor="speed" className="text-xs font-medium cursor-pointer">
                Speed-to-fit (&le; 3s)
              </Label>
              <Switch id="speed" checked={speedToFit} onCheckedChange={setSpeedToFit} />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg border border-border/40 bg-muted/20">
              <Label htmlFor="boom" className="text-xs font-medium cursor-pointer">
                Boomerang Loop
              </Label>
              <Switch id="boom" checked={boomerang} onCheckedChange={setBoomerang} />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg border border-border/40 bg-muted/20">
              <Label htmlFor="alpha" className="text-xs font-medium cursor-pointer">
                Preserve Alpha
              </Label>
              <Switch id="alpha" checked={preserveAlpha} onCheckedChange={setPreserveAlpha} />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg border border-border/40 bg-muted/20">
              <Label htmlFor="overwrite" className="text-xs font-medium cursor-pointer">
                Overwrite Existing
              </Label>
              <Switch id="overwrite" checked={overwrite} onCheckedChange={setOverwrite} />
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg border border-border/40 bg-muted/20">
              <Label htmlFor="recursive" className="text-xs font-medium cursor-pointer">
                Recursive Subfolders
              </Label>
              <Switch id="recursive" checked={recursive} onCheckedChange={setRecursive} />
            </div>
          </div>

          {/* Process Button */}
          <Button
            onClick={handleRunBatch}
            disabled={isProcessing || !folders?.input_files.length}
            className="w-full h-11 text-sm font-semibold bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-600 hover:to-indigo-700 text-white shadow-md shadow-sky-500/20 transition-all cursor-pointer"
          >
            {isProcessing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Processing Folder Videos with VP9 Engine...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4 mr-2" />
                Process All Videos in Folder ({folders?.input_files.length ?? 0})
              </>
            )}
          </Button>

          {batchResult && (
            <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-xs space-y-2">
              <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" /> Batch Conversion Completed!
              </div>
              <div className="grid grid-cols-4 gap-2 pt-1 font-mono">
                <div className="p-2 rounded bg-card/60 text-center">
                  <div className="text-muted-foreground text-[10px]">TOTAL</div>
                  <div className="text-sm font-bold text-foreground">{batchResult.total}</div>
                </div>
                <div className="p-2 rounded bg-card/60 text-center">
                  <div className="text-muted-foreground text-[10px]">SUCCEEDED</div>
                  <div className="text-sm font-bold text-emerald-400">{batchResult.succeeded}</div>
                </div>
                <div className="p-2 rounded bg-card/60 text-center">
                  <div className="text-muted-foreground text-[10px]">SKIPPED</div>
                  <div className="text-sm font-bold text-amber-400">{batchResult.skipped}</div>
                </div>
                <div className="p-2 rounded bg-card/60 text-center">
                  <div className="text-muted-foreground text-[10px]">FAILED</div>
                  <div className="text-sm font-bold text-rose-400">{batchResult.failed}</div>
                </div>
              </div>
            </div>
          )}

          {errorMessage && (
            <Alert variant="destructive" className="border-rose-500/30 bg-rose-500/10 text-rose-300">
              <AlertCircle className="h-4 w-4 text-rose-400" />
              <div className="space-y-1">
                <AlertTitle className="text-xs font-semibold text-rose-300">
                  Batch Processing Failed
                </AlertTitle>
                <AlertDescription className="text-xs text-rose-300/90 leading-relaxed">
                  {errorMessage}
                </AlertDescription>
              </div>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
