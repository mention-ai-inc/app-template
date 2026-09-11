export type ToolAccess = {
  isOrgAdmin: boolean;
};

export const MEMBER_ACCESS: ToolAccess = {
  isOrgAdmin: false,
};

export function decodeOrgRole(token: string): string | null {
  const segments = token.split(".");
  if (segments.length < 2) {
    return null;
  }
  try {
    const payload: unknown = JSON.parse(
      Buffer.from(segments[1]!, "base64url").toString("utf8"),
    );
    if (typeof payload !== "object" || payload === null) {
      return null;
    }
    const orgRole = (payload as Record<string, unknown>).org_role;
    return typeof orgRole === "string" ? orgRole : null;
  } catch {
    return null;
  }
}

export function toolAccessFrom(orgRole: string | null): ToolAccess {
  return { isOrgAdmin: orgRole === "org:admin" };
}

export function canUseOrgAdminTools(access: ToolAccess): boolean {
  return access.isOrgAdmin;
}
