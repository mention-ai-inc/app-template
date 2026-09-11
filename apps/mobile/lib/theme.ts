import { darkColors, lightColors } from "@/lib/theme-colors";

export type ThemeColors = typeof lightColors;

export { darkColors, lightColors };

export function themeColors(isDark: boolean): ThemeColors {
  return isDark ? darkColors : lightColors;
}
