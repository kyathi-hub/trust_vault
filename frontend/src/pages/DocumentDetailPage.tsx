import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Download, Users, ArrowLeft, Shield, Clock } from "lucide-react";
import { useDocumentGrants, useRevokeGrant, useCreateGrant, useDocument } from "@/hooks/useDocuments";
import { useGrantableUsers } from "@/hooks/useUsers";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatBytes, formatDate } from "@/lib/utils";
import { getMemoryToken } from "@/lib/api";
import { toast } from "@/hooks/useToast";
import type { Grant, UserProfile } from "@/types/api";

export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const { data: doc, isLoading, isError } = useDocument(id ?? "");
  const isOwner = doc?.owner_id === user?.id;
  const { data: grants } = useDocumentGrants(isOwner && id ? id : "");
  const revokeMutation = useRevokeGrant(id ?? "");
  const createGrantMutation = useCreateGrant(id ?? "");
  const { data: users } = useGrantableUsers();
  const [showGrantDialog, setShowGrantDialog] = useState(false);
  const [granteeId, setGranteeId] = useState("");
  const [permission, setPermission] = useState<"read" | "edit">("read");
  const [downloading, setDownloading] = useState(false);

  async function handleDownload() {
    if (!id) return;
    setDownloading(true);
    try {
      const token = getMemoryToken() ?? "";
      const resp = await fetch(`/api/v1/documents/${id}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error("Download failed");
      const blob = await resp.blob();
      const disposition = resp.headers.get("Content-Disposition") ?? "";
      const filenameMatch = /filename\*?=(?:UTF-8'')?([^;]+)/i.exec(disposition);
      const filename = filenameMatch ? decodeURIComponent(filenameMatch[1] ?? "document") : "document";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: "Download started", variant: "success" });
    } catch {
      toast({ title: "Download failed", variant: "destructive" });
    } finally {
      setDownloading(false);
    }
  }

  async function handleGrant(e: React.FormEvent) {
    e.preventDefault();
    if (!granteeId) return;
    createGrantMutation.mutate({ grantee_id: granteeId, permission });
    setShowGrantDialog(false);
    setGranteeId("");
  }

  if (isLoading) return (
    <div className="flex justify-center py-12" role="status" aria-label="Loading">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  );

  if (isError || !doc) return (
    <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-destructive" role="alert">
      <p className="font-medium">Document not found</p>
      <p className="text-sm mt-1">This document does not exist or you do not have permission to view it.</p>
      <Button variant="outline" size="sm" className="mt-4" asChild>
        <Link to="/documents">Back to Documents</Link>
      </Button>
    </div>
  );

  const v = doc.current_version;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" asChild aria-label="Back">
          <Link to="/documents"><ArrowLeft className="h-4 w-4" /></Link>
        </Button>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold tracking-tight truncate">{doc.display_name}</h1>
          {doc.description && <p className="text-muted-foreground mt-1">{doc.description}</p>}
        </div>
        <Button onClick={handleDownload} disabled={downloading || v?.scan_status !== "clean"}>
          <Download className="mr-2 h-4 w-4" aria-hidden="true" />
          {downloading ? "Downloading…" : "Download"}
        </Button>
      </div>

      {/* File details */}
      {v && (
        <div className="grid gap-4 rounded-lg border bg-card p-6 sm:grid-cols-2 lg:grid-cols-4">
          <Detail label="File name" value={v.original_filename} />
          <Detail label="Size" value={formatBytes(v.file_size_bytes)} />
          <Detail label="Type" value={v.verified_content_type} />
          <Detail label="Scan status" value={
            <ScanBadge status={v.scan_status} />
          } />
          <Detail label="Version" value={`v${v.version_number}`} />
          <Detail label="Uploaded" value={formatDate(v.created_at)} />
          <Detail label="Modified" value={formatDate(doc.updated_at)} />
          <Detail label="SHA-256" value={
            <span className="font-mono text-xs truncate">{v.checksum_sha256.slice(0, 16)}…</span>
          } />
        </div>
      )}

      {/* Quarantine warning */}
      {v && v.scan_status !== "clean" && (
        <div className="flex items-start gap-3 rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-yellow-800" role="alert">
          <Shield className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          <div className="flex-1">
            <p className="font-medium">Download unavailable</p>
            <p className="text-sm">
              {v.scan_status === "pending" && "This file is queued for malware scanning."}
              {v.scan_status === "infected" && "This file failed malware scanning and cannot be downloaded."}
              {v.scan_status === "skipped" && "This file is quarantined pending malware scanning."}
              {v.scan_status === "error" && "Scanning encountered an error. Contact your administrator."}
            </p>
          </div>
          {/* Dev mode only — approve scan for testing */}
          {isOwner && v.scan_status !== "infected" && (
            <button
              onClick={async () => {
                const token = getMemoryToken() ?? "";
                await fetch(`/api/v1/dev/documents/${id}/approve-scan`, {
                  method: "POST",
                  headers: { Authorization: `Bearer ${token}` },
                });
                window.location.reload();
              }}
              className="shrink-0 rounded bg-yellow-700 px-3 py-1 text-xs text-white hover:bg-yellow-800"
            >
              Approve (dev)
            </button>
          )}
        </div>
      )}

      {/* Access management (owner only) */}
      {isOwner && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5" aria-hidden="true" />
              <h2 className="text-lg font-semibold">Access Control</h2>
            </div>
            <Button size="sm" onClick={() => setShowGrantDialog(true)}>
              Grant Access
            </Button>
          </div>

          {grants && grants.length > 0 ? (
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User ID</TableHead>
                    <TableHead>Permission</TableHead>
                    <TableHead>Granted</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead><span className="sr-only">Actions</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {grants.map((grant) => (
                    <GrantRow
                      key={grant.id}
                      grant={grant}
                      users={users}
                      onRevoke={() => {
                        if (window.confirm("Revoke this access? The user will be denied on their next request.")) {
                          revokeMutation.mutate({ grantId: grant.id });
                        }
                      }}
                    />
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No access grants. Only you can access this document.</p>
          )}
        </div>
      )}

      {/* Grant dialog */}
      <Dialog open={showGrantDialog} onOpenChange={setShowGrantDialog}>
        <DialogContent aria-labelledby="grant-dialog-title">
          <DialogHeader>
            <DialogTitle id="grant-dialog-title">Grant Document Access</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleGrant} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="grantee-select">User</Label>
              <Select value={granteeId} onValueChange={setGranteeId}>
                <SelectTrigger id="grantee-select">
                  <SelectValue placeholder="Select a user…" />
                </SelectTrigger>
                <SelectContent>
                  {users?.filter((u) => u.id !== user?.id && u.is_active).map((u) => (
                    <SelectItem key={u.id} value={u.id}>
                      {u.display_name} ({u.email})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="permission-select">Permission</Label>
              <Select value={permission} onValueChange={(v) => setPermission(v as "read" | "edit")}>
                <SelectTrigger id="permission-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="read">Read — can view and download</SelectItem>
                  <SelectItem value="edit">Edit — can also update metadata and upload new versions</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowGrantDialog(false)}>Cancel</Button>
              <Button type="submit" disabled={!granteeId}>Grant Access</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium">{value}</dd>
    </div>
  );
}

function ScanBadge({ status }: { status: string }) {
  if (status === "clean") return <Badge variant="success">Clean</Badge>;
  if (status === "pending") return <Badge variant="warning">Scanning…</Badge>;
  if (status === "infected") return <Badge variant="destructive">Infected</Badge>;
  return <Badge variant="warning">Quarantined</Badge>;
}

function GrantRow({ grant, users, onRevoke }: { grant: Grant; users?: UserProfile[]; onRevoke: () => void }) {
  const grantee = users?.find((u) => u.id === grant.grantee_id);
  const isRevoked = !!grant.revoked_at;
  const isExpired = grant.expires_at && new Date(grant.expires_at) < new Date();
  const isActive = !isRevoked && !isExpired;

  return (
    <TableRow>
      <TableCell className="text-sm">{grantee ? `${grantee.display_name} (${grantee.email})` : grant.grantee_id.slice(0, 8) + "…"}</TableCell>
      <TableCell><Badge variant={grant.permission === "edit" ? "default" : "secondary"}>{grant.permission}</Badge></TableCell>
      <TableCell className="text-sm text-muted-foreground">{formatDate(grant.created_at)}</TableCell>
      <TableCell className="text-sm text-muted-foreground">
        {grant.expires_at ? (
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" aria-hidden="true" />
            {formatDate(grant.expires_at)}
          </span>
        ) : "Never"}
      </TableCell>
      <TableCell>
        {isRevoked ? <Badge variant="destructive">Revoked</Badge>
          : isExpired ? <Badge variant="warning">Expired</Badge>
          : <Badge variant="success">Active</Badge>}
      </TableCell>
      <TableCell>
        {isActive && (
          <Button variant="ghost" size="sm" onClick={onRevoke} className="text-destructive hover:text-destructive">
            Revoke
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}
