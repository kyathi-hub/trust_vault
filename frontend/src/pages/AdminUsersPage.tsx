import { useState } from "react";
import { UserCheck, UserX, ShieldCheck } from "lucide-react";
import { useUsers, useUpdateUser } from "@/hooks/useUsers";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";
import type { UserProfile, UserRole } from "@/types/api";

export function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const { data: users, isLoading, isError } = useUsers();
  const updateMutation = useUpdateUser();

  function handleRoleChange(user: UserProfile, role: UserRole) {
    if (user.id === currentUser?.id) return;
    if (!window.confirm(`Change ${user.display_name}'s role to ${role}?`)) return;
    updateMutation.mutate({ id: user.id, body: { role } });
  }

  function handleToggleActive(user: UserProfile) {
    const action = user.is_active ? "deactivate" : "reactivate";
    if (!window.confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} ${user.display_name}? ${user.is_active ? "They will be blocked immediately." : ""}`)) return;
    updateMutation.mutate({ id: user.id, body: { is_active: !user.is_active } });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">User Administration</h1>
        <p className="text-muted-foreground">Manage user accounts and roles. Deactivation blocks access immediately.</p>
      </div>

      {isLoading && <div className="flex justify-center py-12" role="status"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>}
      {isError && <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive" role="alert">Failed to load users.</div>}

      {!isLoading && users && (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead><span className="sr-only">Actions</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{u.display_name}</p>
                      <p className="text-xs text-muted-foreground">{u.email}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    {u.id === currentUser?.id ? (
                      <Badge variant="outline">{u.role} (you)</Badge>
                    ) : (
                      <Select value={u.role} onValueChange={(v) => handleRoleChange(u, v as UserRole)}>
                        <SelectTrigger className="w-28 h-8 text-xs" aria-label={`Role for ${u.display_name}`}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="viewer">Viewer</SelectItem>
                          <SelectItem value="owner">Owner</SelectItem>
                          <SelectItem value="admin">Admin</SelectItem>
                        </SelectContent>
                      </Select>
                    )}
                  </TableCell>
                  <TableCell>
                    {u.is_active
                      ? <Badge variant="success">Active</Badge>
                      : <Badge variant="destructive">Deactivated</Badge>}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {u.last_login_at ? formatDate(u.last_login_at) : "Never"}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{formatDate(u.created_at)}</TableCell>
                  <TableCell>
                    {u.id !== currentUser?.id && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleToggleActive(u)}
                        className={u.is_active ? "text-destructive hover:text-destructive" : "text-green-600"}
                        aria-label={u.is_active ? `Deactivate ${u.display_name}` : `Reactivate ${u.display_name}`}
                      >
                        {u.is_active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
                        {u.is_active ? " Deactivate" : " Reactivate"}
                      </Button>
                    )}
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
