import type { paths } from "@packages/acme-api";
import type { QueryClient } from "@tanstack/react-query";
import createFetchClient, {
  type Client,
  type FetchResponse,
  type Middleware,
} from "openapi-fetch";
import createQueryClient from "openapi-react-query";

export type APIErrorData = {
  status_code: number;
  detail: string;
};

export class ApiError extends Error {
  apiError: APIErrorData;

  constructor(message: string, apiError: APIErrorData) {
    super(message);
    this.name = "ApiError";
    this.apiError = apiError;
  }
}

export type APIError = ApiError;

type ResponseData<T extends Record<string | number, any>> = T extends {
  responses: {
    200: {
      content: {
        "application/json": infer U;
      };
    };
  };
}
  ? U
  : T;

export type ApiClientConfig = {
  baseUrl: string;
  getToken: () => Promise<string | null>;
  onApiError?: (error: ApiError) => void;
};

export const getApiClient = (config: ApiClientConfig) => {
  const client = createFetchClient<paths>({
    baseUrl: config.baseUrl,
  });

  client.use(createAuthMiddleware(config));
  return client;
};

export const getApiQueryOptions = (client: Client<paths>) => {
  const queryClient = createQueryClient<paths>(client);
  return queryClient.queryOptions;
};

export const isAPIError = (error: unknown): error is ApiError => {
  return error instanceof ApiError;
};

export const onError = (error: unknown) => {
  if (isAPIError(error)) {
    console.error(error.apiError.detail || "Internal Server Error");
  }
};

const createAuthMiddleware = (config: ApiClientConfig): Middleware => ({
  async onRequest({ request }: { request: Request }) {
    const token = await config.getToken();
    if (!token) throw new Error("Could not get auth token");

    request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },

  async onResponse({ response }) {
    if (response.status >= 400) {
      const body = await response.clone().json();
      const apiErrorData: APIErrorData = {
        status_code: response.status,
        detail: body.detail || `API Error: ${response.status}`,
      };
      const error = new ApiError(apiErrorData.detail, apiErrorData);
      config.onApiError?.(error);
      throw error;
    }
    return response;
  },
});

export function getResponseData<T extends Record<string | number, any>>(
  response: FetchResponse<T, any, any>,
): ResponseData<T> {
  if (!response.data) {
    throw new Error("An unexpected error occurred");
  }
  return response.data;
}

export type ApiContextValue = {
  client: Client<paths>;
  queryClient: QueryClient;
  queryOptions: ReturnType<typeof getApiQueryOptions>;
  baseUrl: string;
};

export type RouterContext = {
  $api: ApiContextValue;
};
