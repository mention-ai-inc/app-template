import type { ReactNode } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";
import { useColorScheme } from "react-native";
import { themeColors } from "@/lib/theme";

type ButtonVariant = "primary" | "secondary" | "ghost" | "destructive";

const buttonClasses: Record<ButtonVariant, string> = {
  primary: "bg-primary dark:bg-primary-dark",
  secondary:
    "border border-border bg-background dark:border-border-dark dark:bg-card-dark",
  ghost: "bg-transparent",
  destructive:
    "border border-destructive/30 bg-destructive/10 dark:border-destructive-dark/40 dark:bg-destructive-dark/15",
};

const labelClasses: Record<ButtonVariant, string> = {
  primary:
    "font-sans-semibold text-primary-foreground dark:text-primary-foreground-dark",
  secondary: "font-sans-semibold text-foreground dark:text-foreground-dark",
  ghost:
    "font-sans-medium text-muted-foreground dark:text-muted-foreground-dark",
  destructive: "font-sans-semibold text-destructive dark:text-destructive-dark",
};

export function Button({
  label,
  onPress,
  variant = "primary",
  pending = false,
  pendingLabel,
  disabled = false,
  icon,
  className,
}: {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  pending?: boolean;
  pendingLabel?: string;
  disabled?: boolean;
  icon?: ReactNode;
  className?: string;
}) {
  const isDisabled = disabled || pending;
  const colors = themeColors(useColorScheme() === "dark");

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      accessibilityRole="button"
      accessibilityState={{ busy: pending, disabled: isDisabled }}
      className={`min-h-control flex-row items-center justify-center rounded-md px-5 active:opacity-75 disabled:opacity-45 ${buttonClasses[variant]} ${className ?? ""}`}
    >
      {pending ? (
        <ActivityIndicator
          size="small"
          color={colors["muted-foreground"]}
          className="mr-2"
        />
      ) : icon ? (
        <View className="mr-2.5">{icon}</View>
      ) : null}
      <Text className={`text-base ${labelClasses[variant]}`}>
        {pending ? (pendingLabel ?? label) : label}
      </Text>
    </Pressable>
  );
}
