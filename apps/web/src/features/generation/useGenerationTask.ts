import { useQuery } from "@tanstack/react-query";
import type { GenerationStatus, GenerationTaskResponse } from "../../lib/api/types";
import { ApiClient } from "../../lib/api/client";

const POLLING_STATUSES: GenerationStatus[] = [
  "queued",
  "running",
  "reviewing",
  "retrying",
];

export function useGenerationTask(
  apiClient: ApiClient,
  taskId: string | null,
) {
  const query = useQuery<GenerationTaskResponse>({
    queryKey: ["generationTask", taskId],
    queryFn: () => apiClient.getGenerationTask(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && POLLING_STATUSES.includes(status)) {
        return 3000;
      }
      return false;
    },
  });

  const isPolling = !!(
    query.data?.status &&
    POLLING_STATUSES.includes(query.data.status)
  );

  const isTerminal = !!(
    query.data?.status &&
    !POLLING_STATUSES.includes(query.data.status)
  );

  return {
    task: query.data ?? null,
    isPolling,
    isTerminal,
    isLoading: query.isLoading,
    error: query.error,
  };
}
