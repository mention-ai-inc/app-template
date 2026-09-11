import { Button } from "@/components/ui";
import { isSessionExistsError, useFinishSignIn } from "@/lib/finish-sign-in";
import { themeColors } from "@/lib/theme";
import { useSignIn } from "@clerk/clerk-expo";
import type { SignInResource } from "@clerk/types";
import { Ionicons } from "@expo/vector-icons";
import * as AppleAuthentication from "expo-apple-authentication";
import * as AuthSession from "expo-auth-session";
import * as Crypto from "expo-crypto";
import * as WebBrowser from "expo-web-browser";
import { useState } from "react";
import { Platform, Text, View, useColorScheme } from "react-native";
import Svg, { Path } from "react-native-svg";

const NO_ACCOUNT_MESSAGE =
  "There's no account for this login. Ask your team admin to invite you.";

export function SSOButtons({
  onError,
}: {
  onError: (message: string) => void;
}) {
  const { signIn, isLoaded } = useSignIn();
  const finishSignIn = useFinishSignIn();
  const isDark = useColorScheme() === "dark";
  const colors = themeColors(isDark);
  const [pending, setPending] = useState<"google" | "apple" | null>(null);

  const completeSignIn = async (attempt: SignInResource) => {
    if (attempt.firstFactorVerification.status === "transferable") {
      onError(NO_ACCOUNT_MESSAGE);
      return;
    }
    if (attempt.status !== "complete") {
      onError("Additional verification is required before you can continue.");
      return;
    }
    if (!(await finishSignIn(attempt.createdSessionId))) {
      onError("Could not complete sign-in.");
    }
  };

  const onGooglePress = async () => {
    if (pending || !isLoaded) return;
    setPending("google");
    try {
      const redirectUrl = AuthSession.makeRedirectUri({ path: "sso-callback" });
      const started = await signIn.create({
        strategy: "oauth_google",
        redirectUrl,
      });
      const authorizeUrl =
        started.firstFactorVerification.externalVerificationRedirectURL;
      if (!authorizeUrl) {
        onError("Could not complete sign-in.");
        return;
      }
      const result = await WebBrowser.openAuthSessionAsync(
        authorizeUrl.toString(),
        redirectUrl,
      );
      if (result.type !== "success") return;
      const rotatingTokenNonce =
        new URL(result.url).searchParams.get("rotating_token_nonce") ?? "";
      await completeSignIn(await started.reload({ rotatingTokenNonce }));
    } catch (err: unknown) {
      if (isSessionExistsError(err) && (await finishSignIn())) return;
      const message =
        err instanceof Error ? err.message : "Could not complete sign-in.";
      onError(message);
    } finally {
      setPending(null);
    }
  };

  const onApplePress = async () => {
    if (pending || !isLoaded) return;
    setPending("apple");
    try {
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
        nonce: Crypto.randomUUID(),
      });
      if (!credential.identityToken) {
        onError("Could not complete sign-in.");
        return;
      }
      await completeSignIn(
        await signIn.create({
          strategy: "oauth_token_apple",
          token: credential.identityToken,
        }),
      );
    } catch (err: unknown) {
      if (isAppleCancellation(err)) return;
      if (isSessionExistsError(err) && (await finishSignIn())) return;
      const message =
        err instanceof Error ? err.message : "Could not complete sign-in.";
      onError(message);
    } finally {
      setPending(null);
    }
  };

  return (
    <View className="w-full gap-stack">
      <View className="my-1 flex-row items-center gap-4">
        <View className="h-px flex-1 bg-muted dark:bg-muted-dark" />
        <Text className="text-sm text-muted-foreground dark:text-muted-foreground-dark dark:text-muted-foreground-dark">
          or
        </Text>
        <View className="h-px flex-1 bg-muted dark:bg-muted-dark" />
      </View>
      <Button
        className="w-full"
        label="Continue with Google"
        pendingLabel="Opening Google…"
        variant="secondary"
        onPress={() => void onGooglePress()}
        disabled={!isLoaded || pending !== null}
        pending={pending === "google"}
        icon={<GoogleIcon />}
      />
      {Platform.OS === "ios" ? (
        <Button
          label="Continue with Apple"
          pendingLabel="Opening Apple…"
          onPress={() => void onApplePress()}
          disabled={!isLoaded || pending !== null}
          pending={pending === "apple"}
          icon={
            <Ionicons
              name="logo-apple"
              size={19}
              color={isDark ? colors["primary-foreground"] : colors.background}
            />
          }
          className="w-full bg-black dark:bg-surface-sunken-dark"
        />
      ) : null}
    </View>
  );
}

function GoogleIcon() {
  return (
    <Svg width={18} height={18} viewBox="0 0 24 24" accessibilityElementsHidden>
      <Path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <Path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <Path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <Path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </Svg>
  );
}

function isAppleCancellation(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    "code" in err &&
    err.code === "ERR_REQUEST_CANCELED"
  );
}
