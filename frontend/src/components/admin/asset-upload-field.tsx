"use client";

import { useRef, useState } from "react";
import Image from "next/image";
import { Upload, Loader2, ImageOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { configurationApi } from "@/lib/configuration-api";
import type { SiteAsset } from "@/types/configuration";

interface AssetUploadFieldProps {
  label: string;
  asset: SiteAsset;
  currentUrl: string;
  onUploaded: (url: string) => void;
}

export function AssetUploadField({ label, asset, currentUrl, onUploaded }: AssetUploadFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Not synced from currentUrl via useState/useEffect: currentUrl
  // starts empty and becomes real once the parent page's async fetch
  // resolves, and useState(currentUrl) would only capture whatever it
  // was at this component's first render, going stale the moment the
  // real value arrives as a later prop update. Only tracks the
  // optimistic value right after a successful upload; otherwise the
  // prop is rendered directly below.
  const [justUploadedUrl, setJustUploadedUrl] = useState<string | null>(null);
  const previewUrl = justUploadedUrl ?? currentUrl;

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      const result = await configurationApi.uploadAsset(asset, file);
      setJustUploadedUrl(result.url);
      onUploaded(result.url);
    } catch {
      setError("Upload failed. Try a smaller image or a different file.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="space-y-1.5">
      <span className="text-sm font-medium text-foreground">{label}</span>
      <div className="flex items-center gap-3 rounded-md border border-border p-3">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-md border border-border bg-secondary">
          {previewUrl ? (
            <Image src={previewUrl} alt={label} width={56} height={56} className="h-full w-full object-contain" unoptimized />
          ) : (
            <ImageOff className="h-5 w-5 text-muted-foreground" />
          )}
        </div>
        <div className="flex-1">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
          >
            {uploading ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <Upload className="mr-2 h-3.5 w-3.5" />}
            {previewUrl ? "Replace" : "Upload"}
          </Button>
          {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>
    </div>
  );
}
