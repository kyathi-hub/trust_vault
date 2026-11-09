import { Link } from "react-router-dom";
import { FileText, Share2, Shield, Users, Upload, AlertTriangle } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useDocuments } from "@/hooks/useDocuments";
import { useAuditEvents } from "@/hooks/useAudit";
import { useUsers } from "@/hooks/useUsers";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

export function DashboardPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const isOwner = user?.role === "owner" || isAdmin;

  const { data: docs } = useDocuments(1);
  const { data: auditData } = useAuditEvents(1, {});
  const { data: users } = useUsers();
  const { data: adminStats } = useQuery({
    queryKey: ["admin", "stats"],
    queryFn: () => api.get<{ total_documents: number; total_users: number; total_audit_events: number; denied_events_24h: number }>("/admin/stats"),
    enabled: isAdmin,
  });

  const myDocs = docs?.items.filter((d) => d.owner_id === user?.id) ?? [];
  const sharedDocs = docs?.items.filter((d) => d.owner_id !== user?.id) ?? [];
  const recentDenials = auditData?.items.filter((e) => e.outcome === "denied").slice(0, 5) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Welcome back, {user?.display_name}</p>
        </div>
        {isOwner && (
          <Button asChild>
            <Link to="/documents/upload">
              <Upload className="mr-2 h-4 w-4" aria-hidden="true" />
              Upload Document
            </Link>
          </Button>
        )}
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={FileText} label="My Documents" value={docs ? String(myDocs.length) : "…"} href="/documents" />
        <StatCard icon={Share2} label="Shared With Me" value={docs ? String(sharedDocs.length) : "…"} href="/shared" />
        {isAdmin && <StatCard icon={FileText} label="Total Documents" value={adminStats ? String(adminStats.total_documents) : "…"} href="/documents" />}
        {isAdmin && <StatCard icon={Users} label="Total Users" value={adminStats ? String(adminStats.total_users) : "…"} href="/admin/users" />}
        {isAdmin && <StatCard icon={Shield} label="Audit Events" value={adminStats ? String(adminStats.total_audit_events) : "…"} href="/admin/audit" />}
        {isAdmin && <StatCard icon={AlertTriangle} label="Denied (24h)" value={adminStats ? String(adminStats.denied_events_24h) : "…"} href="/admin/audit" />}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent documents */}
        <div className="rounded-lg border bg-card p-6">
          <h2 className="mb-4 text-base font-semibold">Recent Documents</h2>
          {docs && docs.items.length > 0 ? (
            <ul className="space-y-3">
              {docs.items.slice(0, 5).map((doc) => (
                <li key={doc.id} className="flex items-center gap-3">
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <div className="min-w-0 flex-1">
                    <Link to={`/documents/${doc.id}`} className="text-sm font-medium hover:underline truncate block">
                      {doc.display_name}
                    </Link>
                    <p className="text-xs text-muted-foreground">{formatDate(doc.updated_at)}</p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No documents yet.</p>
          )}
        </div>

        {/* Recent access denials (admin) or recent activity */}
        {isAdmin ? (
          <div className="rounded-lg border bg-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="h-4 w-4 text-yellow-500" aria-hidden="true" />
              <h2 className="text-base font-semibold">Recent Access Denials</h2>
            </div>
            {recentDenials.length > 0 ? (
              <ul className="space-y-3">
                {recentDenials.map((event) => (
                  <li key={event.id} className="flex items-center gap-3">
                    <Badge variant="destructive" className="shrink-0">denied</Badge>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-mono truncate">{event.action}</p>
                      <p className="text-xs text-muted-foreground">{formatDate(event.occurred_at)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No recent access denials.</p>
            )}
            <Button variant="outline" size="sm" className="mt-4 w-full" asChild>
              <Link to="/admin/audit">View Full Audit Log</Link>
            </Button>
          </div>
        ) : (
          <div className="rounded-lg border bg-card p-6">
            <h2 className="mb-4 text-base font-semibold">Quick Actions</h2>
            <div className="space-y-2">
              {isOwner && (
                <Button variant="outline" className="w-full justify-start" asChild>
                  <Link to="/documents/upload"><Upload className="mr-2 h-4 w-4" />Upload new document</Link>
                </Button>
              )}
              <Button variant="outline" className="w-full justify-start" asChild>
                <Link to="/search"><FileText className="mr-2 h-4 w-4" />Search documents</Link>
              </Button>
              <Button variant="outline" className="w-full justify-start" asChild>
                <Link to="/shared"><Share2 className="mr-2 h-4 w-4" />View shared documents</Link>
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  href: string;
}) {
  return (
    <Link
      to={href}
      className="rounded-lg border bg-card p-6 hover:bg-accent/50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="flex items-center gap-2 text-muted-foreground">
        <Icon className="h-4 w-4" aria-hidden="true" />
        <span className="text-sm font-medium">{label}</span>
      </div>
      <p className="mt-2 text-3xl font-bold">{value}</p>
    </Link>
  );
}
