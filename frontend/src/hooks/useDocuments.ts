import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Document, DocumentListResponse, Grant } from "@/types/api";
import { toast } from "./useToast";

export const docKeys = {
  all: ["documents"] as const,
  list: (page: number, q?: string) => ["documents", "list", page, q] as const,
  detail: (id: string) => ["documents", id] as const,
  grants: (id: string) => ["documents", id, "grants"] as const,
  shared: (page: number) => ["documents", "shared", page] as const,
};

export function useDocuments(page = 1, q?: string) {
  return useQuery({
    queryKey: docKeys.list(page, q),
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (q) params.set("q", q);
      return api.get<DocumentListResponse>(`/documents?${params}`);
    },
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: docKeys.detail(id),
    queryFn: () => api.get<Document>(`/documents/${id}`),
    enabled: !!id,
  });
}

export function useDocumentGrants(documentId: string) {
  return useQuery({
    queryKey: docKeys.grants(documentId),
    queryFn: () => api.get<Grant[]>(`/documents/${documentId}/grants`),
    enabled: !!documentId,
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/documents/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: docKeys.all });
      toast({ title: "Document deleted", variant: "success" });
    },
    onError: () => toast({ title: "Delete failed", variant: "destructive" }),
  });
}

export function useRevokeGrant(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ grantId, reason }: { grantId: string; reason?: string }) =>
      api.delete(`/documents/${documentId}/grants/${grantId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: docKeys.grants(documentId) });
      toast({ title: "Access revoked", variant: "success" });
    },
    onError: () => toast({ title: "Revoke failed", variant: "destructive" }),
  });
}

export function useCreateGrant(documentId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { grantee_id: string; permission: string; expires_at?: string }) =>
      api.post<Grant>(`/documents/${documentId}/grants`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: docKeys.grants(documentId) });
      toast({ title: "Access granted", variant: "success" });
    },
    onError: () => toast({ title: "Grant failed", variant: "destructive" }),
  });
}

export function useSearchDocuments(q: string, page = 1) {
  return useQuery({
    queryKey: ["search", q, page],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (q) params.set("q", q);
      return api.get<DocumentListResponse>(`/search/documents?${params}`);
    },
    enabled: q.length > 0,
  });
}
