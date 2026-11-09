import { Lock } from "lucide-react";

interface Props {
  message?: string;
}

export function LoadingScreen({ message = "Loading…" }: Props) {
  return (
    <div
      className="flex h-screen flex-col items-center justify-center gap-4 bg-background"
      role="status"
      aria-label={message}
    >
      <div className="flex items-center gap-3">
        <Lock className="h-8 w-8 animate-pulse text-primary" aria-hidden="true" />
        <span className="text-2xl font-semibold text-foreground">TrustVault</span>
      </div>
      <p className="text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
