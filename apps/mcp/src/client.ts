import type { paths } from "@packages/acme-api";
import createFetchClient, { type Client } from "openapi-fetch";

export type ApiClient = Client<paths>;

export function normalizeApiUrl(apiUrl: string): string {
  const url = new URL(apiUrl.trim());
  return url.origin;
}

export function createApiClient(apiKey: string, apiUrl: string): ApiClient {
  const client = createFetchClient<paths>({
    baseUrl: normalizeApiUrl(apiUrl),
  });

  client.use({
    async onRequest({ request }) {
      request.headers.set("Authorization", `Bearer ${apiKey}`);
      return request;
    },
  });

  return client;
}
