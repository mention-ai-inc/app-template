import { useAuth } from "@clerk/clerk-expo";

export function useIsOrgAdmin(): boolean {
  const { orgRole } = useAuth();
  return orgRole === "org:admin";
}
