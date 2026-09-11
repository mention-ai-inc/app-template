import { ApiError } from "../client";

export const POLL_INTERVAL = 2000;

export type QueryOptions = {
  enabled?: boolean;
  refetchInterval?: number | false | ((query: any) => number | false);
  refetchOnWindowFocus?: boolean | "always";
  refetchOnMount?: boolean | "always";
  refetchOnReconnect?: boolean | "always";
  retry?: boolean | number;
  retryDelay?: number | ((attempt: number) => number);
  staleTime?: number;
  gcTime?: number;
};

function isApiErrorResponse(error: unknown): error is { detail: string } {
  return (
    typeof error === "object" &&
    error !== null &&
    "detail" in error &&
    typeof (error as { detail: unknown }).detail === "string"
  );
}

export function throwIfError<T>(response: {
  data?: T;
  error?: unknown;
  response: Response;
}): T {
  if (response.error) {
    const errorDetail = isApiErrorResponse(response.error)
      ? response.error.detail
      : "An error occurred";
    throw new ApiError(errorDetail, {
      status_code: response.response.status,
      detail: errorDetail,
    });
  }
  return response.data as T;
}
