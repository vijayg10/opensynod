import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiJson } from "@/lib/api";
import type { Panel } from "@/types/api";

export const panelKeys = {
  all: ["panels"] as const,
  detail: (id: string) => ["panels", id] as const,
};

export function usePanels() {
  return useQuery({
    queryKey: panelKeys.all,
    queryFn: () => apiJson<Panel[]>("/api/v1/panels"),
  });
}

export function usePanel(id: string) {
  return useQuery({
    queryKey: panelKeys.detail(id),
    queryFn: () => apiJson<Panel>(`/api/v1/panels/${id}`),
    enabled: !!id,
  });
}

export function useCreatePanel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (panel: Partial<Panel>) =>
      apiJson<Panel>("/api/v1/panels", {
        method: "POST",
        body: JSON.stringify(panel),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: panelKeys.all });
    },
  });
}

export function useUpdatePanel(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (panel: Partial<Panel>) =>
      apiJson<Panel>(`/api/v1/panels/${id}`, {
        method: "PATCH",
        body: JSON.stringify(panel),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: panelKeys.all });
      void queryClient.invalidateQueries({ queryKey: panelKeys.detail(id) });
    },
  });
}
