import { useCallback } from "react";
import { useToast } from "@chakra-ui/react";
import { useQueryClient } from "@tanstack/react-query";
import {
  deleteRelease as deleteReleaseApi,
  pauseRelease as pauseReleaseApi,
  resumeRelease as resumeReleaseApi,
} from "../../services/api";
import { releasesKeys } from "../../lib/queryKeys";

interface OperationOptions {
  onSuccess?: () => void;
}

export const useReleaseOperations = (requestId?: string) => {
  const queryClient = useQueryClient();
  const toast = useToast();

  const invalidateReleaseQueries = useCallback(async () => {
    const tasks: Array<Promise<unknown>> = [
      queryClient.invalidateQueries({ queryKey: releasesKeys.all }),
      queryClient.invalidateQueries({ queryKey: releasesKeys.list(undefined), exact: false }),
    ];

    if (requestId) {
      tasks.push(
        queryClient.invalidateQueries({ queryKey: releasesKeys.byRequest(requestId), exact: true }),
      );
      tasks.push(
        queryClient.invalidateQueries({ queryKey: releasesKeys.list({ requestId }), exact: true }),
      );
    }

    await Promise.all(tasks);
  }, [queryClient, requestId]);

  const handleError = useCallback(
    (title: string, error: unknown) => {
      const message = error instanceof Error ? error.message : undefined;
      toast({
        title,
        description: message,
        status: "error",
        duration: 4000,
        isClosable: true,
      });
    },
    [toast],
  );

  const deleteRelease = useCallback(
    async (releaseId: string, options?: OperationOptions) => {
      try {
        await deleteReleaseApi(releaseId);
        toast({
          title: "Release deleted",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
        await invalidateReleaseQueries();
        options?.onSuccess?.();
      } catch (error) {
        console.error("Failed to delete release", error);
        handleError("Failed to delete release", error);
        throw error;
      }
    },
    [handleError, invalidateReleaseQueries, toast],
  );

  const pauseRelease = useCallback(
    async (releaseId: string, options?: OperationOptions) => {
      try {
        await pauseReleaseApi(releaseId);
        toast({
          title: "Release paused",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
        await invalidateReleaseQueries();
        options?.onSuccess?.();
      } catch (error) {
        console.error("Failed to pause release", error);
        handleError("Failed to pause release", error);
        throw error;
      }
    },
    [handleError, invalidateReleaseQueries, toast],
  );

  const resumeRelease = useCallback(
    async (releaseId: string, options?: OperationOptions) => {
      try {
        await resumeReleaseApi(releaseId);
        toast({
          title: "Release resumed",
          status: "success",
          duration: 3000,
          isClosable: true,
        });
        await invalidateReleaseQueries();
        options?.onSuccess?.();
      } catch (error) {
        console.error("Failed to resume release", error);
        handleError("Failed to resume release", error);
        throw error;
      }
    },
    [handleError, invalidateReleaseQueries, toast],
  );

  return {
    deleteRelease,
    pauseRelease,
    resumeRelease,
  } as const;
};

