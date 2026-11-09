import { Link, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  Share2,
  Search,
  Users,
  Shield,
  Upload,
  Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
  ownerOnly?: boolean;
}

const navItems: NavItem[] = [
  { label: "Dashboard",      href: "/",               icon: LayoutDashboard },
  { label: "My Documents",   href: "/documents",       icon: FileText },
  { label: "Upload",         href: "/documents/upload", icon: Upload, ownerOnly: true },
  { label: "Shared With Me", href: "/shared",           icon: Share2 },
  { label: "Search",         href: "/search",           icon: Search },
];

const adminItems: NavItem[] = [
  { label: "Users",          href: "/admin/users",     icon: Users,   adminOnly: true },
  { label: "Audit Log",      href: "/admin/audit",     icon: Shield,  adminOnly: true },
];

export function Sidebar() {
  const { pathname } = useLocation();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const isOwner = user?.role === "owner" || isAdmin;

  return (
    <aside
      className="flex w-64 flex-col border-r border-sidebar-border bg-sidebar"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-6">
        <Lock className="h-6 w-6 text-sidebar-primary" aria-hidden="true" />
        <span className="text-lg font-semibold text-sidebar-foreground">TrustVault</span>
      </div>

      {/* Role badge */}
      {user && (
        <div className="px-6 py-3">
          <span className={cn(
            "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
            isAdmin
              ? "bg-red-900/40 text-red-300"
              : isOwner
                ? "bg-blue-900/40 text-blue-300"
                : "bg-gray-700 text-gray-300"
          )}>
            {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
          </span>
        </div>
      )}

      <nav className="flex-1 space-y-1 px-3 py-2" aria-label="Primary navigation">
        {navItems.map((item) => {
          if (item.ownerOnly && !isOwner) return null;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              to={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}

        {isAdmin && (
          <>
            <div className="my-3 border-t border-sidebar-border" />
            <p className="px-3 py-1 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/50">
              Administration
            </p>
            {adminItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  to={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                  {item.label}
                </Link>
              );
            })}
          </>
        )}
      </nav>
    </aside>
  );
}
