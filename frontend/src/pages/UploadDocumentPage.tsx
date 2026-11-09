import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileText, X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, AppError } from "@/lib/api";
import { formatBytes } from "@/lib/utils";
import { docKeys } from "@/hooks/useDocuments";
import { toast } from "@/hooks/useToast";

const ALLOWED_EXTENSIONS = ["pdf","docx","doc","xlsx","xls","pptx","ppt","txt","csv","png","jpg","jpeg","gif","webp","zip"];
const MAX_SIZE_BYTES = 50 * 1024 * 1024;

export function UploadDocumentPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    if (!f) return;

    // Client-side pre-checks (server validation is authoritative)
    const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(`File type ".${ext}" is not allowed.`);
      return;
    }
    if (f.size > MAX_SIZE_BYTES) {
      setError(`File too large. Maximum size is ${formatBytes(MAX_SIZE_BYTES)}.`);
      return;
    }

    setFile(f);
    setError(null);
    if (!displayName) setDisplayName(f.name.replace(/\.[^.]+$/, ""));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !displayName.trim()) return;

    setUploading(true);
    setError(null);

    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("display_name", displayName.trim());
      fd.append("description", description);

      await api.upload("/documents", fd);
      qc.invalidateQueries({ queryKey: docKeys.all });
      toast({ title: "Document uploaded successfully", variant: "success" });
      navigate("/documents");
    } catch (err) {
      if (err instanceof AppError) {
        setError(err.userMessage);
      } else {
        setError("Upload failed. Please try again.");
      }
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Upload Document</h1>
        <p className="text-muted-foreground">Files are encrypted at rest and scanned for malware.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6" noValidate>
        {/* File drop zone */}
        <div>
          <Label htmlFor="file-input">File</Label>
          <div
            className="mt-1 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-input p-8 transition-colors hover:border-primary"
            onClick={() => fileInputRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Click to select a file"
          >
            {file ? (
              <div className="flex items-center gap-3">
                <FileText className="h-8 w-8 text-primary" aria-hidden="true" />
                <div>
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-muted-foreground">{formatBytes(file.size)}</p>
                </div>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setFile(null); setDisplayName(""); }}
                  className="ml-2 rounded p-1 hover:bg-accent"
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <>
                <Upload className="mb-2 h-10 w-10 text-muted-foreground" aria-hidden="true" />
                <p className="text-sm font-medium">Click to select or drag and drop</p>
                <p className="text-xs text-muted-foreground mt-1">
                  PDF, DOCX, XLSX, images, ZIP — max {formatBytes(MAX_SIZE_BYTES)}
                </p>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            id="file-input"
            type="file"
            className="sr-only"
            accept={ALLOWED_EXTENSIONS.map((e) => `.${e}`).join(",")}
            onChange={handleFileChange}
            aria-label="Select file"
          />
        </div>

        {/* Display name */}
        <div className="space-y-1">
          <Label htmlFor="display-name">Document name <span aria-hidden="true">*</span></Label>
          <Input
            id="display-name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="e.g. Q3 Financial Report"
            required
            maxLength={500}
            aria-required="true"
          />
        </div>

        {/* Description */}
        <div className="space-y-1">
          <Label htmlFor="description">Description</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description…"
            rows={3}
            maxLength={5000}
          />
        </div>

        {error && (
          <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive" role="alert">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <Button type="submit" disabled={!file || !displayName.trim() || uploading}>
            {uploading ? "Uploading…" : "Upload Document"}
          </Button>
          <Button type="button" variant="outline" onClick={() => navigate("/documents")}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
