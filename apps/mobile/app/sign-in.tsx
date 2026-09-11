import { SSOButtons } from "@/components/sso-buttons";
import { Button, Field, Screen } from "@/components/ui";
import { isSessionExistsError, useFinishSignIn } from "@/lib/finish-sign-in";
import { useAuth, useSignIn } from "@clerk/clerk-expo";
import { Redirect } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";

export default function SignInScreen() {
  const { isSignedIn } = useAuth({ treatPendingAsSignedOut: false });
  const { signIn, isLoaded } = useSignIn();
  const finishSignIn = useFinishSignIn();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (isSignedIn) {
    return <Redirect href="/" />;
  }

  const onSubmit = async () => {
    if (!isLoaded || submitting) return;
    setError(null);
    setSubmitting(true);
    try {
      const attempt = await signIn.create({ identifier: email, password });
      if (attempt.status === "complete") {
        if (!(await finishSignIn(attempt.createdSessionId))) {
          setError("Could not sign in.");
        }
      } else {
        setError(
          "Additional verification is required before you can continue. Check your email for a verification code, or try signing in again.",
        );
      }
    } catch (err: unknown) {
      if (isSessionExistsError(err) && (await finishSignIn())) return;
      const message = err instanceof Error ? err.message : "Could not sign in.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen title="Sign in">
      <View className="gap-stack">
        <Field
          label="Email"
          accessibilityLabel="Email"
          placeholder="Email"
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <Field
          label="Password"
          accessibilityLabel="Password"
          placeholder="Password"
          autoComplete="current-password"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />
        {error ? (
          <Text className="text-sm leading-5 text-red-600 dark:text-red-400">
            {error}
          </Text>
        ) : null}
        <Button
          label="Sign in"
          pendingLabel="Signing in…"
          pending={submitting}
          disabled={!isLoaded || !email.trim() || !password}
          onPress={() => void onSubmit()}
          className="mt-1 w-full"
        />
        <SSOButtons onError={setError} />
      </View>
    </Screen>
  );
}
