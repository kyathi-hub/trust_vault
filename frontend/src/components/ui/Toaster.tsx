import { ToastProvider, ToastViewport, Toast, ToastTitle, ToastDescription, ToastClose } from "./toast";
import { useToastState } from "@/hooks/useToast";

export function Toaster() {
  const { toasts, dismiss } = useToastState();
  return (
    <ToastProvider>
      {toasts.map((t) => (
        <Toast key={t.id} variant={t.variant} onOpenChange={(open) => !open && dismiss(t.id)}>
          <div className="grid gap-1">
            <ToastTitle>{t.title}</ToastTitle>
            {t.description && <ToastDescription>{t.description}</ToastDescription>}
          </div>
          <ToastClose />
        </Toast>
      ))}
      <ToastViewport />
    </ToastProvider>
  );
}
