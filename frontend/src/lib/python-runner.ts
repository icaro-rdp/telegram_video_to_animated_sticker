import { execFile } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export const TEMP_DIR = path.join(os.tmpdir(), "tg_sticker_web");

if (!fs.existsSync(TEMP_DIR)) {
  fs.mkdirSync(TEMP_DIR, { recursive: true });
}

/**
 * Locate the root directory of the telegram_video_to_animated_sticker project.
 */
export function getRepoRoot(): string {
  const current = process.cwd();
  // Check parent (when running inside frontend/)
  const parent = path.resolve(current, "..");
  if (fs.existsSync(path.join(parent, "pyproject.toml"))) {
    return parent;
  }
  // Check current directory (when running from root)
  if (fs.existsSync(path.join(current, "pyproject.toml"))) {
    return current;
  }
  return parent;
}

/**
 * Execute the tg-sticker CLI through uv inside the project root.
 */
export async function runTgSticker(args: string[]): Promise<{ stdout: string; stderr: string }> {
  const repoRoot = getRepoRoot();
  try {
    const result = await execFileAsync("uv", ["run", "tg-sticker", ...args], {
      cwd: repoRoot,
      maxBuffer: 50 * 1024 * 1024,
    });
    return result;
  } catch (error: unknown) {
    const err = error as { stdout?: string; stderr?: string; message?: string };
    if (err.stdout && err.stdout.trim().startsWith("{")) {
      return { stdout: err.stdout, stderr: err.stderr || "" };
    }
    throw new Error(err.stderr || err.message || "Failed to execute tg-sticker command");
  }
}
