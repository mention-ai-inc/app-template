import { ActivityIndicator, Text, View, useColorScheme } from "react-native";
import { themeColors } from "@/lib/theme";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  const colors = themeColors(useColorScheme() === "dark");

  return (
    <View className="flex-1 items-center justify-center bg-background px-screen dark:bg-background-dark">
      <ActivityIndicator size="large" color={colors.primary} />
      <Text className="mt-4 text-base text-muted-foreground dark:text-muted-foreground-dark">
        {label}
      </Text>
    </View>
  );
}
