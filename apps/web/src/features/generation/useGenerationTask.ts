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
const TIMEZONE_SUFFIX_PATTERN = /(Z|[+-]\d{2}:?\d{2})$/i;

export function parseGenerationTaskTimestamp(timestamp: string): number {
  const normalizedTimestamp = TIMEZONE_SUFFIX_PATTERN.test(timestamp)
    ? timestamp
    : `${timestamp}Z`;
  return new Date(normalizedTimestamp).getTime();
}

function isGenerationTaskStale(createdAt: string | undefined): boolean {
  if (!createdAt) return false;
  return Date.now() - parseGenerationTaskTimestamp(createdAt) > STALE_THRESHOLD_MS;
}

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
      if (isGenerationTaskStale(createdAt)) {
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
    isGenerationTaskStale(query.data.createdAt)
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
