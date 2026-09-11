import { Feather } from "@expo/vector-icons";
import { Text, View, useColorScheme } from "react-native";
import { themeColors } from "@/lib/theme";

export function EmptyState({
  icon,
  title,
  description,
}: {
  icon: keyof typeof Feather.glyphMap;
  title: string;
  description?: string;
}) {
  const colors = themeColors(useColorScheme() === "dark");

  return (
    <View className="flex-1 items-center justify-center px-screen py-16">
      <View className="mb-5 h-16 w-16 items-center justify-center rounded-lg bg-surface-sunken dark:bg-surface-sunken-dark">
        <Feather name={icon} size={26} color={colors["muted-foreground"]} />
      </View>
      <Text className="font-sans-semibold text-xl text-foreground dark:text-foreground-dark">
        {title}
      </Text>
      {description ? (
        <Text className="mt-2 max-w-sm text-center font-sans text-base leading-6 text-muted-foreground dark:text-muted-foreground-dark">
          {description}
        </Text>
      ) : null}
    </View>
  );
}
