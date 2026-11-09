import { LogOut, User } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";

export function TopBar() {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-background px-6">
      {/* Skip to main content — accessibility */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:rounded focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Skip to main content
      </a>

      <div />

      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <User className="h-4 w-4" aria-hidden="true" />
            <span>{user.display_name}</span>
          </div>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={logout}
          aria-label="Sign out"
        >
          <LogOut className="mr-2 h-4 w-4" aria-hidden="true" />
          Sign out
        </Button>
      </div>
    </header>
  );
}
