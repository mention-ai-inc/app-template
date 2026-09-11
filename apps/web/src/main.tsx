import { ClerkLoaded, ClerkProvider, useAuth } from "@clerk/react";
import { dark } from "@clerk/themes";
import {
  ApiProvider,
  getApiClient,
  getApiQueryOptions,
  type ApiContextValue,
} from "@packages/acme-api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRouter, RouterProvider } from "@tanstack/react-router";
import { StrictMode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Toaster } from "sonner";
import { CmdEnterSubmitHandler } from "@/components/cmd-enter-submit";
import { ThemeProvider, useTheme } from "@/components/theme-provider";
import "@/main.css";
import { routeTree } from "@/routeTree.gen";
import type { AppUser } from "@/routes/__root";

const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
const API_BASE_PATH = `https://${import.meta.env.VITE_FEATURE_ENVIRONMENT ?? ""}api.acme.example.com`;
const CLERK_TEMPLATE = "main";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (
          (error as any)?.apiError?.status_code >= 400 &&
          (error as any)?.apiError?.status_code < 500
        ) {
          return false;
        }

        return failureCount < 3;
      },
    },
    mutations: {
      onError: (error) => {
        console.error("Mutation error:", error);
      },
    },
  },
});

const router = createRouter({
  routeTree,
  context: {
    $api: undefined as unknown as ApiContextValue,
    user: undefined as unknown as AppUser,
  },
  defaultPreload: "intent",
  defaultPreloadStaleTime: 0,
  scrollRestoration: true,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

function App() {
  const auth = useAuth();

  const apiContext: ApiContextValue = useMemo(() => {
    const client = getApiClient({
      baseUrl: API_BASE_PATH,
      getToken: () => auth.getToken({ template: CLERK_TEMPLATE }),
    });
    return {
      client,
      queryClient,
      queryOptions: getApiQueryOptions(client),
      baseUrl: API_BASE_PATH,
    };
  }, [auth]);

  const appUser: AppUser = {
    user_id: auth.userId ?? "",
    org_role:
      auth.orgRole === "org:admin"
        ? "admin"
        : auth.orgRole == "org:member"
          ? "member"
          : "unknown",
    org_id: auth.orgId ?? "",
  };

  return (
    <ApiProvider value={apiContext}>
      <RouterProvider
        router={router}
        context={{ $api: apiContext, user: appUser }}
      />
    </ApiProvider>
  );
}

function ClerkWrapper({ children }: { children: React.ReactNode }) {
  const { theme } = useTheme();
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("dark");

  useEffect(() => {
    const getResolvedTheme = () => {
      if (theme === "system") {
        return window.matchMedia("(prefers-color-scheme: dark)").matches
          ? "dark"
          : "light";
      }
      return theme as "light" | "dark";
    };

    setResolvedTheme(getResolvedTheme());

    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handler = (e: MediaQueryListEvent) => {
        setResolvedTheme(e.matches ? "dark" : "light");
      };
      mediaQuery.addEventListener("change", handler);
      return () => mediaQuery.removeEventListener("change", handler);
    }
  }, [theme]);

  return (
    <ClerkProvider
      publishableKey={CLERK_PUBLISHABLE_KEY}
      afterSignOutUrl="/"
      appearance={{
        theme: resolvedTheme === "dark" ? dark : undefined,
      }}
    >
      {children}
    </ClerkProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark" storageKey="ui-theme">
        <ClerkWrapper>
          <ClerkLoaded>
            <CmdEnterSubmitHandler />
            <App />
            <Toaster />
          </ClerkLoaded>
        </ClerkWrapper>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
