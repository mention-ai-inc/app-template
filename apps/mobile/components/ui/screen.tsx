import type { ReactNode } from "react";
import { ScrollView, Text, View } from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

export function Screen({
  title,
  description,
  eyebrow,
  children,
  footer,
  serifTitle = false,
}: {
  title: string;
  description?: string;
  eyebrow?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  serifTitle?: boolean;
}) {
  const insets = useSafeAreaInsets();

  return (
    <SafeAreaView
      className="flex-1 bg-background dark:bg-background-dark"
      edges={["top"]}
    >
      <ScrollView
        className="flex-1"
        contentContainerClassName="flex-grow px-screen py-8"
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {eyebrow ? <View className="mb-8">{eyebrow}</View> : null}
        <Text
          className={`leading-10 tracking-tight text-foreground dark:text-foreground-dark ${
            serifTitle ? "font-serif text-4xl" : "font-sans-semibold text-3xl"
          }`}
        >
          {title}
        </Text>
        {description ? (
          <Text className="mt-3 font-sans text-base leading-7 text-muted-foreground dark:text-muted-foreground-dark">
            {description}
          </Text>
        ) : null}
        <View className="mt-section flex-1">{children}</View>
      </ScrollView>
      {footer ? (
        <View
          className="border-t border-border-subtle bg-background px-screen pt-footer dark:border-border-subtle-dark dark:bg-background-dark"
          style={{ paddingBottom: Math.max(insets.bottom, 16) }}
        >
          {footer}
        </View>
      ) : null}
    </SafeAreaView>
  );
}
