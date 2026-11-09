import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { UserProfile } from "@/types/api";
import { toast } from "./useToast";

export const userKeys = {
  all: ["users"] as const,
  list: () => ["users", "list"] as const,
  detail: (id: string) => ["users", id] as const,
};

export function useUsers() {
  return useQuery({
    queryKey: userKeys.list(),
    queryFn: () => api.get<UserProfile[]>("/users"),
  });
}

export function useGrantableUsers() {
  return useQuery({
    queryKey: ["users", "grantable"],
    queryFn: () => api.get<UserProfile[]>("/users/grantable"),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: { role?: string; is_active?: boolean } }) =>
      api.patch<UserProfile>(`/users/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: userKeys.all });
      toast({ title: "User updated", variant: "success" });
    },
    onError: () => toast({ title: "Update failed", variant: "destructive" }),
  });
}
