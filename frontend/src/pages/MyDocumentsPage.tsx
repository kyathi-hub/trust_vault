import { useState } from "react";
import { Link } from "react-router-dom";
import { FileText, Plus, Trash2, Eye, Search } from "lucide-react";
import { useDocuments, useDeleteDocument } from "@/hooks/useDocuments";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatBytes, formatDate } from "@/lib/utils";
import type { Document } from "@/types/api";

function ScanBadge({ status }: { status: string }) {
  if (status === "clean") return <Badge variant="success">Clean</Badge>;
  if (status === "pending") return <Badge variant="warning">Scanning…</Badge>;
  if (status === "infected") return <Badge variant="destructive">Infected</Badge>;
  if (status === "skipped") return <Badge variant="warning">Quarantined</Badge>;
  return <Badge variant="outline">{status}</Badge>;
}

export function MyDocumentsPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const { data, isLoading, isError } = useDocuments(page, search || undefined);
  const deleteMutation = useDeleteDocument();
  const isOwner = user?.role === "owner" || user?.role === "admin";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My Documents</h1>
          <p className="text-muted-foreground">Documents you own and documents shared with you.</p>
        </div>
        {isOwner && (
          <Button asChild>
            <Link to="/documents/upload">
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              Upload Document
            </Link>
          </Button>
        )}
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input
          placeholder="Search documents…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="pl-9"
          aria-label="Search documents"
        />
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12" role="status" aria-label="Loading documents">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive" role="alert">
          Failed to load documents. Please try again.
        </div>
      )}

      {!isLoading && !isError && data && (
        <>
          {data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
              <FileText className="mb-4 h-12 w-12 text-muted-foreground" aria-hidden="true" />
              <p className="text-lg font-medium">No documents yet</p>
              <p className="text-sm text-muted-foreground">
                {isOwner ? "Upload your first document to get started." : "No documents have been shared with you yet."}
              </p>
            </div>
          ) : (
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Size</TableHead>
                    <TableHead>Scan</TableHead>
                    <TableHead>Modified</TableHead>
                    <TableHead><span className="sr-only">Actions</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((doc) => (
                    <DocumentRow
                      key={doc.id}
                      doc={doc}
                      isOwner={isOwner && doc.owner_id === user?.id}
                      onDelete={(id) => deleteMutation.mutate(id)}
                    />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Pagination */}
          {data.total > data.page_size && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {data.total} documents total
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>Previous</Button>
                <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)} disabled={page * data.page_size >= data.total}>Next</Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function DocumentRow({
  doc,
  isOwner,
  onDelete,
}: {
  doc: Document;
  isOwner: boolean;
  onDelete: (id: string) => void;
}) {
  const v = doc.current_version;
  return (
    <TableRow>
      <TableCell>
        <Link
          to={`/documents/${doc.id}`}
          className="font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        >
          {/* display_name is output-encoded by React — safe */}
          {doc.display_name}
        </Link>
        {doc.description && (
          <p className="text-xs text-muted-foreground truncate max-w-xs">{doc.description}</p>
        )}
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">
        {v?.verified_content_type.split("/").pop()?.toUpperCase() ?? "—"}
      </TableCell>
      <TableCell className="text-sm">{v ? formatBytes(v.file_size_bytes) : "—"}</TableCell>
      <TableCell>{v ? <ScanBadge status={v.scan_status} /> : "—"}</TableCell>
      <TableCell className="text-sm text-muted-foreground">{formatDate(doc.updated_at)}</TableCell>
      <TableCell>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" asChild aria-label={`View ${doc.display_name}`}>
            <Link to={`/documents/${doc.id}`}>
              <Eye className="h-4 w-4" />
            </Link>
          </Button>
          {isOwner && (
            <Button
              variant="ghost"
              size="icon"
              aria-label={`Delete ${doc.display_name}`}
              onClick={() => {
                if (window.confirm(`Delete "${doc.display_name}"? This can be restored later.`)) {
                  onDelete(doc.id);
                }
              }}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}
