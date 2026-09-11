import { OrganizationList } from "@clerk/react";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/switcher")({
  component: RouteComponent,
});

function RouteComponent() {
  return (
    <div className="flex flex-col items-center justify-center h-screen w-full">
      <OrganizationList
        afterSelectOrganizationUrl="/"
        afterCreateOrganizationUrl="/"
        hidePersonal={true}
        skipInvitationScreen={true}
      />
    </div>
  );
}
