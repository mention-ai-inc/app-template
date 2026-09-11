import { isClerkAPIResponseError, useClerk } from "@clerk/clerk-expo";
import { useRouter } from "expo-router";

export function useFinishSignIn() {
  const clerk = useClerk();
  const router = useRouter();

  return async (createdSessionId?: string | null): Promise<boolean> => {
    const client = await clerk.client.reload();
    const session =
      client.signedInSessions.find(
        (candidate) => candidate.id === createdSessionId,
      ) ?? client.signedInSessions[0];
    if (!session) return false;

    let organization: string | undefined;
    if (session.status === "pending") {
      if (session.currentTask?.key !== "choose-organization") return false;
      organization = session.user?.organizationMemberships[0]?.organization.id;
    }

    await clerk.setActive({ session: session.id, organization });
    router.replace("/");
    return true;
  };
}

export function isSessionExistsError(err: unknown): boolean {
  return (
    isClerkAPIResponseError(err) &&
    err.errors.some((error) => error.code === "session_exists")
  );
}
