import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { StoryProjectResponse, CreateStoryProjectRequest } from "../../lib/api/types";
import { ApiClient } from "../../lib/api/client";

export function useStories(apiClient: ApiClient) {
  const queryClient = useQueryClient();

  const listQuery = useQuery<StoryProjectResponse[]>({
    queryKey: ["storyProjects"],
    queryFn: () => apiClient.listStoryProjects(),
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateStoryProjectRequest) =>
      apiClient.createStoryProject(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["storyProjects"] });
    },
  });

  return {
    stories: listQuery.data ?? [],
    isLoading: listQuery.isLoading,
    createStory: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
  };
}
