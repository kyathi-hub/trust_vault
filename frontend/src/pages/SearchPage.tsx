import { useState } from "react";
import { Link } from "react-router-dom";
import { Search as SearchIcon, Eye } from "lucide-react";
import { useSearchDocuments } from "@/hooks/useDocuments";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatBytes, formatDate } from "@/lib/utils";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useSearchDocuments(submitted, page);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(query.trim());
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Search</h1>
        <p className="text-muted-foreground">Search only returns documents you are authorised to access.</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 max-w-lg" role="search">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by document name…"
            className="pl-9"
            aria-label="Search query"
            maxLength={200}
          />
        </div>
        <Button type="submit">Search</Button>
      </form>

      {isLoading && (
        <div className="flex justify-center py-8" role="status">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      )}

      {!isLoading && submitted && data && (
        <>
          <p className="text-sm text-muted-foreground">
            {data.total} result{data.total !== 1 ? "s" : ""} for &ldquo;{submitted}&rdquo;
          </p>

          {data.items.length === 0 ? (
            <div className="rounded-lg border border-dashed py-12 text-center text-muted-foreground">
              No accessible documents match your search.
            </div>
          ) : (
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
                  {data.items.map((doc) => (
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

          {data.total > data.page_size && (
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>Previous</Button>
              <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)} disabled={page * data.page_size >= data.total}>Next</Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
