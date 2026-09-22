import fs from "node:fs";
import path from "node:path";
import { NextResponse } from "next/server";
import { getRepoRoot } from "@/lib/python-runner";

export async function GET() {
  const repoRoot = getRepoRoot();
  const inDir = path.join(repoRoot, "input_videos");
  const outDir = path.join(repoRoot, "output_stickers");

  if (!fs.existsSync(inDir)) {
    fs.mkdirSync(inDir, { recursive: true });
  }
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  const inputFiles = fs
    .readdirSync(inDir, { withFileTypes: true })
    .filter((d) => d.isFile())
    .map((d) => d.name);

  const outputFiles = fs
    .readdirSync(outDir, { withFileTypes: true })
    .filter((d) => d.isFile() && d.name.endsWith(".webm"))
    .map((d) => d.name);

  return NextResponse.json({
    input_dir: inDir,
    output_dir: outDir,
    input_files: inputFiles,
    output_files: outputFiles,
  });
}
