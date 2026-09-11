import { type ApiContextValue } from "@packages/acme-api-client";
import { RedirectToSignIn, Show } from "@clerk/react";
import {
  createRootRouteWithContext,
  Outlet,
  redirect,
} from "@tanstack/react-router";
import { NotFoundComponent } from "@/components/page-states/not-found";

export interface AppUser {
  user_id: string;
  org_role: "admin" | "member" | "unknown";
  org_id: string;
}

export interface AppContext {
  $api: ApiContextValue;
  user: AppUser;
}

export const Route = createRootRouteWithContext<AppContext>()({
  beforeLoad: ({ context, location }) => {
    if (
      context.user.org_role === "unknown" &&
      location.pathname !== "/switcher"
    ) {
      throw redirect({ to: "/switcher" });
    }
  },
  component: Layout,
  notFoundComponent: NotFoundComponent,
});

function Layout() {
  return (
    <>
      <Show when="signed-in">
        <Outlet />
      </Show>
      <Show when="signed-out">
        <RedirectToSignIn />
      </Show>
    </>
  );
}
