import { useAuth } from "@clerk/clerk-expo";
import {
  getApiClient,
  getApiQueryOptions,
  type ApiContextValue,
} from "@packages/acme-api-client";
import { focusManager, QueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { AppState } from "react-native";

const FEATURE_ENVIRONMENT = process.env.EXPO_PUBLIC_FEATURE_ENVIRONMENT ?? "";
const API_BASE_URL = `https://${FEATURE_ENVIRONMENT}api.acme.example.com`;
const CLERK_TEMPLATE = "main";

AppState.addEventListener("change", (status) => {
  focusManager.setFocused(status === "active");
});

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10000,
      retry: (failureCount, error) => {
        const status = (error as { apiError?: { status_code?: number } })
          ?.apiError?.status_code;
        if (status !== undefined && status >= 400 && status < 500) return false;
        return failureCount < 3;
      },
    },
  },
});

export function useApiContext(): ApiContextValue {
  const auth = useAuth();
  return useMemo(() => {
    const client = getApiClient({
      baseUrl: API_BASE_URL,
      getToken: () => auth.getToken({ template: CLERK_TEMPLATE }),
    });
    return {
      client,
      queryClient,
      queryOptions: getApiQueryOptions(client),
      baseUrl: API_BASE_URL,
    };
  }, [auth]);
}
