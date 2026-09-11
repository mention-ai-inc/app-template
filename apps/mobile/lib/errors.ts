import { isAPIError } from "@packages/acme-api-client";

export function getErrorMessage(
  error: unknown,
  fallback = "An error occurred",
): string {
  if (isAPIError(error)) {
    return error.apiError.detail || fallback;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  if (typeof error === "string") {
    return error;
  }
  return fallback;
}
