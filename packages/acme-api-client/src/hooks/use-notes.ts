import type { components } from "@packages/acme-api";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useApi } from "../context";
import { queryKeys } from "../queries/keys";
import { createNoteMutation, createNotesQueryOptions } from "../queries/notes";
import type { QueryOptions } from "../queries/utils";

export function useNotes({ options }: { options?: QueryOptions } = {}) {
  const $api = useApi();
  const queryOptions = createNotesQueryOptions({ $api });
  return useQuery({ ...queryOptions, ...options });
}

export function useCreateNote() {
  const $api = useApi();

  return useMutation({
    mutationFn: (data: components["schemas"]["CreateNoteRequest"]) =>
      createNoteMutation($api, data),
    onSuccess: () => {
      $api.queryClient.invalidateQueries({
        queryKey: queryKeys.notes.base(),
      });
    },
  });
}
