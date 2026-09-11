const { lightColors, darkColors } = require("./lib/theme-colors");

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: lightColors.background,
          dark: darkColors.background,
        },
        foreground: {
          DEFAULT: lightColors.foreground,
          dark: darkColors.foreground,
        },
        card: {
          DEFAULT: lightColors.card,
          dark: darkColors.card,
        },
        "surface-raised": {
          DEFAULT: lightColors["surface-raised"],
          dark: darkColors["surface-raised"],
        },
        "surface-sunken": {
          DEFAULT: lightColors["surface-sunken"],
          dark: darkColors["surface-sunken"],
        },
        primary: {
          DEFAULT: lightColors.primary,
          dark: darkColors.primary,
          foreground: lightColors["primary-foreground"],
          "foreground-dark": darkColors["primary-foreground"],
        },
        secondary: {
          DEFAULT: lightColors.secondary,
          dark: darkColors.secondary,
          foreground: lightColors["secondary-foreground"],
          "foreground-dark": darkColors["secondary-foreground"],
        },
        muted: {
          DEFAULT: lightColors.muted,
          dark: darkColors.muted,
          foreground: lightColors["muted-foreground"],
          "foreground-dark": darkColors["muted-foreground"],
        },
        accent: {
          DEFAULT: lightColors.accent,
          dark: darkColors.accent,
        },
        brand: {
          DEFAULT: lightColors.brand,
          dark: darkColors.brand,
          foreground: lightColors["brand-foreground"],
          "foreground-dark": darkColors["brand-foreground"],
          subtle: lightColors["brand-subtle"],
          "subtle-dark": darkColors["brand-subtle"],
          "subtle-foreground": lightColors["brand-subtle-foreground"],
          "subtle-foreground-dark": darkColors["brand-subtle-foreground"],
        },
        success: {
          DEFAULT: lightColors.success,
          dark: darkColors.success,
        },
        warning: {
          DEFAULT: lightColors.warning,
          dark: darkColors.warning,
        },
        destructive: {
          DEFAULT: lightColors.destructive,
          dark: darkColors.destructive,
        },
        info: {
          DEFAULT: lightColors.info,
          dark: darkColors.info,
        },
        border: {
          DEFAULT: lightColors.border,
          dark: darkColors.border,
          subtle: lightColors["border-subtle"],
          "subtle-dark": darkColors["border-subtle"],
        },
        ring: {
          DEFAULT: lightColors.ring,
          dark: darkColors.ring,
        },
      },
      fontFamily: {
        sans: ["Inter_400Regular"],
        "sans-medium": ["Inter_500Medium"],
        "sans-semibold": ["Inter_600SemiBold"],
        serif: ["InstrumentSerif_400Regular"],
      },
      spacing: {
        screen: "24px",
        section: "32px",
        stack: "16px",
        tight: "8px",
        card: "24px",
        footer: "16px",
      },
      borderRadius: {
        sm: "6px",
        md: "8px",
        lg: "10px",
        xl: "14px",
        "2xl": "18px",
        control: "8px",
        surface: "10px",
        ask: "18px",
      },
      minHeight: {
        control: "44px",
      },
    },
  },
  plugins: [],
};
