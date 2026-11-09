import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuditListResponse, ChainVerifyResult } from "@/types/api";
import { toast } from "./useToast";

export function useAuditEvents(page = 1, filters: Record<string, string> = {}) {
  return useQuery({
    queryKey: ["audit", "events", page, filters],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      Object.entries(filters).forEach(([k, v]) => v && params.set(k, v));
      return api.get<AuditListResponse>(`/admin/audit?${params}`);
    },
  });
}

export function useVerifyAuditChain() {
  return useQuery({
    queryKey: ["audit", "verify"],
    queryFn: () => api.get<ChainVerifyResult>("/admin/audit/verify"),
    staleTime: 0,
  });
}

export function useCreateCheckpoint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/audit/checkpoint"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["audit"] });
      toast({ title: "Checkpoint created", variant: "success" });
    },
    onError: () => toast({ title: "Checkpoint failed", variant: "destructive" }),
  });
}
