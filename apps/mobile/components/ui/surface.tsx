import type { ReactNode } from "react";
import { View } from "react-native";

export function Surface({
  children,
  tone = "default",
  className,
}: {
  children: ReactNode;
  tone?: "default" | "muted";
  className?: string;
}) {
  return (
    <View
      className={`rounded-lg border p-card ${
        tone === "muted"
          ? "border-border bg-surface-sunken dark:border-border-dark dark:bg-surface-sunken-dark"
          : "border-border bg-card dark:border-border-dark dark:bg-card-dark"
      } ${className ?? ""}`}
    >
      {children}
    </View>
  );
}
