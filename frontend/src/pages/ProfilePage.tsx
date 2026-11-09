import { useAuth } from "@/contexts/AuthContext";

export function ProfilePage() {
  const { user } = useAuth();
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
      <div className="rounded-lg border bg-card p-6 space-y-2 max-w-sm">
        <div><span className="text-sm text-muted-foreground">Name</span><p className="font-medium">{user?.display_name}</p></div>
        <div><span className="text-sm text-muted-foreground">Email</span><p className="font-medium">{user?.email}</p></div>
        <div><span className="text-sm text-muted-foreground">Role</span><p className="font-medium capitalize">{user?.role}</p></div>
      </div>
    </div>
  );
}
