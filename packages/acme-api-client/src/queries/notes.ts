import type { components } from "@packages/acme-api";
import type { RouterContext } from "../client";
import { POLL_INTERVAL, throwIfError } from "./utils";

export function hasUnsummarizedNotes(
  data: components["schemas"]["ListNotesResponse"] | undefined,
): boolean {
  return data?.notes.some((note) => note.status !== "summarized") ?? false;
}

export function createNotesQueryOptions({
  $api,
}: {
  $api: RouterContext["$api"];
}) {
  return {
    ...$api.queryOptions("get", "/rest/notes/notes"),
    refetchInterval: (query: {
      state: { data?: components["schemas"]["ListNotesResponse"] };
    }) => (hasUnsummarizedNotes(query.state.data) ? POLL_INTERVAL : false),
  };
}

export async function createNoteMutation(
  $api: RouterContext["$api"],
  data: components["schemas"]["CreateNoteRequest"],
) {
  const response = await $api.client.POST("/rest/notes/notes", { body: data });
  return throwIfError(response);
}
