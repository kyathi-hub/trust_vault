import { Link } from "react-router-dom";
import { ShieldOff } from "lucide-react";
import { Button } from "@/components/ui/button";

export function AccessDeniedPage() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
      <ShieldOff className="h-12 w-12 text-destructive" aria-hidden="true" />
      <h1 className="text-2xl font-bold">Access Denied</h1>
      <p className="max-w-md text-muted-foreground">
        You do not have permission to access this area. If you believe this is a mistake,
        contact your administrator.
      </p>
      <Button asChild variant="outline">
        <Link to="/">Go to Dashboard</Link>
      </Button>
    </div>
  );
}
