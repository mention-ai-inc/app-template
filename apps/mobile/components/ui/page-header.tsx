import type { ReactNode } from "react";
import { Text, View } from "react-native";

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <View className="border-b border-border-subtle bg-background px-screen pb-5 pt-3 dark:border-border-subtle-dark dark:bg-background-dark">
      <View className="flex-row items-center justify-between gap-4">
        <Text className="flex-1 text-3xl font-semibold tracking-tight text-foreground dark:text-foreground-dark">
          {title}
        </Text>
        {action}
      </View>
      {description ? (
        <Text className="mt-2 max-w-xl text-base leading-6 text-muted-foreground dark:text-muted-foreground-dark">
          {description}
        </Text>
      ) : null}
    </View>
  );
}
