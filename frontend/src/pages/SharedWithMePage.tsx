import { useState } from "react";
import { Link } from "react-router-dom";
import { Share2, Eye } from "lucide-react";
import { useDocuments } from "@/hooks/useDocuments";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatBytes, formatDate } from "@/lib/utils";

export function SharedWithMePage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const { data, isLoading } = useDocuments(page);

  // Filter to documents not owned by current user (i.e., shared with them)
  const sharedDocs = data?.items.filter((d) => d.owner_id !== user?.id) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Shared With Me</h1>
        <p className="text-muted-foreground">Documents other users have granted you access to.</p>
      </div>

      {isLoading && (
        <div className="flex justify-center py-12" role="status">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}

      {!isLoading && sharedDocs.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
          <Share2 className="mb-4 h-12 w-12 text-muted-foreground" aria-hidden="true" />
          <p className="text-lg font-medium">Nothing shared with you yet</p>
          <p className="text-sm text-muted-foreground">When someone grants you access, documents will appear here.</p>
        </div>
      )}

      {!isLoading && sharedDocs.length > 0 && (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Modified</TableHead>
                <TableHead><span className="sr-only">Actions</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sharedDocs.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell>
                    <Link to={`/documents/${doc.id}`} className="font-medium hover:underline">
                      {doc.display_name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-sm">{doc.current_version ? formatBytes(doc.current_version.file_size_bytes) : "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{formatDate(doc.updated_at)}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" asChild aria-label={`View ${doc.display_name}`}>
                      <Link to={`/documents/${doc.id}`}><Eye className="h-4 w-4" /></Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
