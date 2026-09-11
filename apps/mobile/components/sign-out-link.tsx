import { useAuth } from "@clerk/clerk-expo";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Text } from "react-native";

export function SignOutLink() {
  const { signOut } = useAuth();
  const router = useRouter();
  const [pending, setPending] = useState(false);

  const onPress = async () => {
    if (pending) return;
    setPending(true);
    try {
      await signOut();
    } finally {
      setPending(false);
      router.replace("/sign-in");
    }
  };

  return (
    <Text
      accessibilityRole="button"
      disabled={pending}
      onPress={() => void onPress()}
      className="min-h-11 py-3 text-center text-base font-medium text-muted-foreground dark:text-muted-foreground-dark"
    >
      Sign in with a different account
    </Text>
  );
}
