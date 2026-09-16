import { Text, TextInput, View, type TextInputProps } from "react-native";
import { useColorScheme } from "react-native";
import { themeColors } from "@/lib/theme";

export function Field({
  label,
  hint,
  error,
  className,
  multiline,
  ...inputProps
}: TextInputProps & {
  label: string;
  hint?: string;
  error?: string | null;
  className?: string;
}) {
  const colors = themeColors(useColorScheme() === "dark");

  return (
    <View className="gap-tight">
      <Text className="font-medium text-base text-foreground dark:text-foreground-dark">
        {label}
      </Text>
      <TextInput
        {...inputProps}
        multiline={multiline}
        placeholderTextColor={colors["muted-foreground"]}
        className={`w-full rounded-md border border-border bg-card px-4 text-[16px] text-foreground dark:border-border-dark dark:bg-transparent dark:text-foreground-dark ${
          multiline ? "min-h-[112px] py-4" : "min-h-control py-3"
        } ${error ? "border-destructive dark:border-destructive-dark" : ""} ${className ?? ""}`}
      />
      {error ? (
        <Text className="text-sm leading-5 text-destructive dark:text-destructive-dark">
          {error}
        </Text>
      ) : hint ? (
        <Text className="text-sm leading-5 text-muted-foreground dark:text-muted-foreground-dark">
          {hint}
        </Text>
      ) : null}
    </View>
  );
}
