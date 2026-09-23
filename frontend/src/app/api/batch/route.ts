import { type NextRequest, NextResponse } from "next/server";
import { runTgSticker } from "@/lib/python-runner";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const payload = await request.json();

    const args = ["batch", "-i", "input_videos", "-o", "output_stickers", "--json"];

    if (payload.mode === "emoji" || payload.mode === "sticker") {
      args.push("--mode", payload.mode);
    }

    if (payload.duration && !Number.isNaN(Number(payload.duration))) {
      args.push("-t", String(payload.duration));
    }

    if (payload.speed_to_fit) {
      args.push("--speed-to-fit");
    }

    if (payload.loop_mode === "pingpong") {
      args.push("--pingpong");
    }

    if (
      payload.fit_mode &&
      ["contain", "crop", "pad", "stretch"].includes(payload.fit_mode)
    ) {
      args.push("--fit", payload.fit_mode);
    }

    if (payload.crop && typeof payload.crop === "string" && payload.crop.trim()) {
      args.push("--crop", payload.crop.trim());
    }

    if (payload.fps && !Number.isNaN(Number(payload.fps))) {
      args.push("--fps", String(payload.fps));
    }

    if (payload.crf && !Number.isNaN(Number(payload.crf))) {
      args.push("--crf", String(payload.crf));
    }

    if (payload.remove_bg && typeof payload.remove_bg === "string" && payload.remove_bg.trim()) {
      args.push("--remove-bg", payload.remove_bg.trim());
    }

    if (payload.overwrite) {
      args.push("--overwrite");
    }

    if (payload.recursive) {
      args.push("-r");
    }

    const { stdout } = await runTgSticker(args);
    const parsed = JSON.parse(stdout.trim());

    return NextResponse.json(parsed);
  } catch (error: unknown) {
    const err = error as Error;
    return NextResponse.json(
      { error: err.message || "Failed to process batch conversion" },
      { status: 400 }
    );
  }
}
