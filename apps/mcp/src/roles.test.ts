import {
  canUseOrgAdminTools,
  decodeOrgRole,
  MEMBER_ACCESS,
  toolAccessFrom,
} from "@/roles";
import { describe, expect, it } from "vitest";

function makeToken(payload: object): string {
  return `header.${Buffer.from(JSON.stringify(payload)).toString("base64url")}.signature`;
}

describe("decodeOrgRole", () => {
  it("reads org_role from a JWT payload", () => {
    expect(decodeOrgRole(makeToken({ org_role: "org:admin" }))).toBe(
      "org:admin",
    );
    expect(decodeOrgRole(makeToken({ org_role: "org:member" }))).toBe(
      "org:member",
    );
  });

  it("returns null when the claim is absent or not a string", () => {
    expect(decodeOrgRole(makeToken({ sub: "user_123" }))).toBeNull();
    expect(decodeOrgRole(makeToken({ org_role: 7 }))).toBeNull();
  });

  it("returns null for malformed tokens", () => {
    expect(decodeOrgRole("garbage")).toBeNull();
    expect(decodeOrgRole("a.%%%.c")).toBeNull();
    expect(
      decodeOrgRole(`a.${Buffer.from("[1,2]").toString("base64url")}.c`),
    ).toBeNull();
  });
});

describe("toolAccessFrom", () => {
  it("marks org admins", () => {
    expect(canUseOrgAdminTools(toolAccessFrom("org:admin"))).toBe(true);
  });

  it("treats members and unknown roles as member-only", () => {
    expect(canUseOrgAdminTools(toolAccessFrom("org:member"))).toBe(false);
    expect(toolAccessFrom(null)).toEqual(MEMBER_ACCESS);
  });
});
