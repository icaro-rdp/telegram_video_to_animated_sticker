import fs from "node:fs";
import path from "node:path";
import { type NextRequest, NextResponse } from "next/server";
import { runTgSticker, TEMP_DIR } from "@/lib/python-runner";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  let tempIn: string | null = null;
  try {
    const formData = await request.formData();
    const video = formData.get("video") as File | null;

    if (!video || video.size === 0) {
      return NextResponse.json(
        { error: "Uploaded video file is empty" },
        { status: 400 }
      );
    }

    const rawFilename = (formData.get("filename") as string) || video.name || "video.mp4";
    const ext = path.extname(rawFilename) || ".mp4";
    const baseStem = path.basename(rawFilename, ext).replace(/[^a-zA-Z0-9_-]/g, "_");
    const uniqueId = `${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;

    tempIn = path.join(TEMP_DIR, `input_${uniqueId}${ext}`);
    const outFilename = `${baseStem}_telegram_${uniqueId}.webm`;
    const tempOut = path.join(TEMP_DIR, outFilename);

    const arrayBuffer = await video.arrayBuffer();
    await fs.promises.writeFile(tempIn, Buffer.from(arrayBuffer));

    const args = ["convert", tempIn, "-o", tempOut, "--json"];

    const mode = formData.get("mode") as string | null;
    if (mode === "emoji" || mode === "sticker") {
      args.push("--mode", mode);
    }

    const startTime = formData.get("start_time") as string | null;
    if (startTime && !Number.isNaN(Number(startTime))) {
      args.push("-ss", startTime);
    }

    const duration = formData.get("duration") as string | null;
    if (duration && !Number.isNaN(Number(duration))) {
      args.push("-t", duration);
    }

    const speedToFit = formData.get("speed_to_fit");
    if (speedToFit === "true" || speedToFit === "1") {
      args.push("--speed-to-fit");
    }

    const loopMode = formData.get("loop_mode") as string | null;
    if (loopMode === "pingpong") {
      args.push("--pingpong");
    }

    const fitMode = formData.get("fit_mode") as string | null;
    if (fitMode && ["contain", "crop", "pad", "stretch"].includes(fitMode)) {
      args.push("--fit", fitMode);
    }

    const fps = formData.get("fps") as string | null;
    if (fps && !Number.isNaN(Number(fps))) {
      args.push("--fps", fps);
    }

    const crf = formData.get("crf") as string | null;
    if (crf && !Number.isNaN(Number(crf))) {
      args.push("--crf", crf);
    }

    const removeBg = formData.get("remove_bg") as string | null;
    if (removeBg && removeBg.trim()) {
      args.push("--remove-bg", removeBg.trim());
    }

    const { stdout } = await runTgSticker(args);
    const parsed = JSON.parse(stdout.trim());

    parsed.download_url = `/output/${outFilename}`;
    parsed.filename = outFilename;

    return NextResponse.json(parsed);
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { error: err.message || "Failed to convert video" },
      { status: 400 }
    );
  } finally {
    if (tempIn && fs.existsSync(tempIn)) {
      fs.promises.unlink(tempIn).catch(() => {});
    }
  }
}
