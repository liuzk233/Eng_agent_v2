import { useQuery } from "@tanstack/react-query";
import type { GenerationStatus, GenerationTaskResponse } from "../../lib/api/types";
import { ApiClient } from "../../lib/api/client";

const POLLING_STATUSES: GenerationStatus[] = [
  "queued",
  "running",
  "reviewing",
  "retrying",
];

const STALE_THRESHOLD_MS = 300_000; // 5 minutes

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
      if (!status || !POLLING_STATUSES.includes(status)) return false;
      const createdAt = query.state.data?.createdAt;
      if (createdAt && Date.now() - new Date(createdAt).getTime() > STALE_THRESHOLD_MS) {
        return false;
      }
      return 3000;
    },
  });

  const isPolling = !!(
    query.data?.status &&
    POLLING_STATUSES.includes(query.data.status)
  );

  const isStale = !!(
    query.data?.status &&
    POLLING_STATUSES.includes(query.data.status) &&
    query.data.createdAt &&
    Date.now() - new Date(query.data.createdAt).getTime() > STALE_THRESHOLD_MS
  );

  const isTerminal = !!(
    query.data?.status &&
    !POLLING_STATUSES.includes(query.data.status)
  );

  return {
    task: query.data ?? null,
    isPolling,
    isStale,
    isTerminal,
    isLoading: query.isLoading,
    error: query.error,
  };
}
