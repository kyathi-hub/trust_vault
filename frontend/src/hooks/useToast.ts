import { useState, useCallback } from "react";

export interface ToastMessage {
  id: string;
  title: string;
  description?: string;
  variant?: "default" | "destructive" | "success";
}

let toastHandlers: ((msg: ToastMessage) => void)[] = [];

export function toast(msg: Omit<ToastMessage, "id">) {
  const id = crypto.randomUUID();
  toastHandlers.forEach((h) => h({ ...msg, id }));
}

export function useToastState() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((msg: ToastMessage) => {
    setToasts((prev) => [...prev, msg]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== msg.id));
    }, 4000);
  }, []);

  // Register handler
  useState(() => {
    toastHandlers.push(addToast);
    return () => {
      toastHandlers = toastHandlers.filter((h) => h !== addToast);
    };
  });

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, dismiss };
}
