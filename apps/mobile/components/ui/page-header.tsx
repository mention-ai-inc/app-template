import type { ReactNode } from "react";
import { Text, View } from "react-native";

export function PageHeader({
  title,
  description,
  action,
  serifTitle = false,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  serifTitle?: boolean;
}) {
  return (
    <View className="border-b border-border-subtle bg-background px-screen pb-5 pt-3 dark:border-border-subtle-dark dark:bg-background-dark">
      <View className="flex-row items-center justify-between gap-4">
        <Text
          className={`flex-1 tracking-tight text-foreground dark:text-foreground-dark ${
            serifTitle
              ? "font-serif text-4xl leading-10"
              : "font-sans-semibold text-3xl"
          }`}
        >
          {title}
        </Text>
        {action}
      </View>
      {description ? (
        <Text className="mt-2 max-w-xl font-sans text-base leading-6 text-muted-foreground dark:text-muted-foreground-dark">
          {description}
        </Text>
      ) : null}
    </View>
  );
}
