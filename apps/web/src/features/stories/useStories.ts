import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { StoryProjectResponse, CreateStoryProjectRequest } from "../../lib/api/types";
import { ApiClient } from "../../lib/api/client";

interface RenameStoryVariables {
  storyProjectId: string;
  title: string;
}

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

  const renameMutation = useMutation({
    mutationFn: ({ storyProjectId, title }: RenameStoryVariables) =>
      apiClient.renameStoryProject(storyProjectId, { title }),
    onSuccess: (renamedStory) => {
      queryClient.setQueryData<StoryProjectResponse[]>(["storyProjects"], (current) => {
        if (!current) {
          return [renamedStory];
        }
        return current.map((story) =>
          story.id === renamedStory.id ? renamedStory : story,
        );
      });
    },
  });

  return {
    stories: listQuery.data ?? [],
    isLoading: listQuery.isLoading,
    createStory: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    renameStory: (storyProjectId: string, title: string) =>
      renameMutation.mutateAsync({ storyProjectId, title }),
    isRenaming: renameMutation.isPending,
  };
}
