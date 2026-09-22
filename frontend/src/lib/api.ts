/**
 * Typed client API utilities for Telegram Sticker Converter backend.
 */

export interface MediaInfo {
  width: number;
  height: number;
  duration: number;
  fps: number;
  size_bytes: number;
  size_kb: number;
  codec: string;
  has_audio: boolean;
  has_alpha: boolean;
}

export interface ConvertResponse {
  success: boolean;
  valid: boolean;
  issues: string[];
  download_url: string;
  filename: string;
  info: MediaInfo | null;
  error?: string;
  error_type?: string;
}

export interface FolderResponse {
  input_dir: string;
  output_dir: string;
  input_files: string[];
  output_files: string[];
}

export interface BatchPayload {
  mode: string;
  duration?: number;
  speed_to_fit: boolean;
  loop_mode: string;
  fit_mode?: string;
  fps: number;
  crf: number;
  remove_bg?: string;
  preserve_alpha: boolean;
  overwrite: boolean;
  recursive: boolean;
}

export interface BatchResponse {
  success: boolean;
  total: number;
  succeeded: number;
  skipped: number;
  failed: number;
  error?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function checkApiStatus(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) {
    throw new Error(`API status check failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchFolders(): Promise<FolderResponse> {
  const res = await fetch(`${API_BASE}/api/folders`);
  if (!res.ok) {
    throw new Error(`Failed to fetch folders: ${res.statusText}`);
  }
  return res.json();
}

export async function convertSingleVideo(formData: FormData): Promise<ConvertResponse> {
  const res = await fetch(`${API_BASE}/api/convert`, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  if (!res.ok || data.error) {
    throw new Error(data.error || `Conversion failed with status ${res.status}`);
  }
  return data;
}

export async function runBatchProcess(payload: BatchPayload): Promise<BatchResponse> {
  const res = await fetch(`${API_BASE}/api/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok || data.error) {
    throw new Error(data.error || `Batch processing failed with status ${res.status}`);
  }
  return data;
}
