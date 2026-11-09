import { useState } from "react";
import { Shield, CheckCircle, XCircle, AlertTriangle, RefreshCw } from "lucide-react";
import { useAuditEvents, useVerifyAuditChain, useCreateCheckpoint } from "@/hooks/useAudit";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate } from "@/lib/utils";

export function AdminAuditPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const { data, isLoading, refetch } = useAuditEvents(page, filters);
  const { data: chainStatus, refetch: recheckChain, isFetching: checkingChain } = useVerifyAuditChain();
  const checkpointMutation = useCreateCheckpoint();

  function handleFilterChange(key: string, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Audit Log</h1>
          <p className="text-muted-foreground">Tamper-evident SHA-256 hash chain. No document content is shown here.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => recheckChain()} disabled={checkingChain}>
            <RefreshCw className={`mr-2 h-4 w-4 ${checkingChain ? "animate-spin" : ""}`} aria-hidden="true" />
            Verify Chain
          </Button>
          <Button size="sm" onClick={() => checkpointMutation.mutate()} disabled={checkpointMutation.isPending}>
            <Shield className="mr-2 h-4 w-4" aria-hidden="true" />
            {checkpointMutation.isPending ? "Creating…" : "Create Checkpoint"}
          </Button>
        </div>
      </div>

      {/* Chain integrity status */}
      {chainStatus && (
        <div className={`flex items-start gap-3 rounded-lg border p-4 ${chainStatus.valid ? "border-green-200 bg-green-50 text-green-800" : "border-red-200 bg-red-50 text-red-800"}`} role="status">
          {chainStatus.valid
            ? <CheckCircle className="h-5 w-5 shrink-0 mt-0.5" aria-hidden="true" />
            : <XCircle className="h-5 w-5 shrink-0 mt-0.5" aria-hidden="true" />}
          <div>
            <p className="font-medium">
              {chainStatus.valid ? "Chain integrity verified" : "Chain integrity FAILED"}
            </p>
            <p className="text-sm">
              {chainStatus.events_checked} events checked.
              {chainStatus.valid ? " No anomalies detected." : ` ${chainStatus.anomalies.length} anomaly(s) detected.`}
            </p>
            {!chainStatus.valid && chainStatus.anomalies.map((a, i) => (
              <p key={i} className="text-xs mt-1 font-mono">{a.type}: {a.detail}</p>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-1">
          <Label htmlFor="filter-action">Action</Label>
          <Input id="filter-action" placeholder="e.g. document:download" onChange={(e) => handleFilterChange("action", e.target.value)} aria-label="Filter by action" />
        </div>
        <div className="space-y-1">
          <Label htmlFor="filter-outcome">Outcome</Label>
          <Input id="filter-outcome" placeholder="success / denied / error" onChange={(e) => handleFilterChange("outcome", e.target.value)} aria-label="Filter by outcome" />
        </div>
        <div className="space-y-1">
          <Label htmlFor="filter-actor">Actor ID</Label>
          <Input id="filter-actor" placeholder="User ID" onChange={(e) => handleFilterChange("actor_id", e.target.value)} aria-label="Filter by actor" />
        </div>
      </div>

      {isLoading && <div className="flex justify-center py-8" role="status"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>}

      {!isLoading && data && (
        <>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">#</TableHead>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Outcome</TableHead>
                  <TableHead>Target</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.length === 0 ? (
                  <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-8">No audit events match your filters.</TableCell></TableRow>
                ) : data.items.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell className="font-mono text-xs text-muted-foreground">{event.sequence}</TableCell>
                    <TableCell className="text-sm">{formatDate(event.occurred_at)}</TableCell>
                    <TableCell className="text-sm">
                      <span className="font-mono text-xs">{event.actor_email ?? event.actor_id?.slice(0, 8) ?? "system"}</span>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{event.action}</TableCell>
                    <TableCell>
                      {event.outcome === "success"
                        ? <Badge variant="success">success</Badge>
                        : event.outcome === "denied"
                          ? <Badge variant="destructive">denied</Badge>
                          : <Badge variant="warning">{event.outcome}</Badge>}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {event.target_type && <span>{event.target_type}/</span>}
                      {event.target_id && <span className="font-mono">{event.target_id.slice(0, 8)}…</span>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {data.total > data.page_size && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">{data.total} events total</p>
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
