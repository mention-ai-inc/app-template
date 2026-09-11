// eslint-disable-next-line no-restricted-imports
import "../global.css";
import { RootErrorBoundary } from "@/components/error-boundary";
import { queryClient, useApiContext } from "@/lib/api";
import { CLERK_PUBLISHABLE_KEY } from "@/lib/clerk";
import { appFonts } from "@/lib/fonts";
import { darkColors, lightColors, themeColors } from "@/lib/theme";
import {
  ClerkLoaded,
  ClerkLoading,
  ClerkProvider,
  useAuth,
} from "@clerk/clerk-expo";
import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from "@react-navigation/native";
import { tokenCache } from "@clerk/clerk-expo/token-cache";
import { useFonts } from "expo-font";
import { BottomSheetModalProvider } from "@gorhom/bottom-sheet";
import { ApiProvider } from "@packages/acme-api-client";
import { QueryClientProvider } from "@tanstack/react-query";
import { Slot } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import * as WebBrowser from "expo-web-browser";
import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Text, View, useColorScheme } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import {
  KeyboardAvoidingView,
  KeyboardProvider,
} from "react-native-keyboard-controller";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { Toaster } from "sonner-native";

WebBrowser.maybeCompleteAuthSession();
void SplashScreen.preventAutoHideAsync();

const SLOW_CONNECTION_MS = 10000;

const lightNavigationTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: lightColors.background,
    card: lightColors.card,
    text: lightColors.foreground,
    border: lightColors.border,
    primary: lightColors.primary,
  },
};

const darkNavigationTheme = {
  ...DarkTheme,
  colors: {
    ...DarkTheme.colors,
    background: darkColors.background,
    card: darkColors.card,
    text: darkColors.foreground,
    border: darkColors.border,
    primary: darkColors.primary,
  },
};

function ClerkLoadingScreen() {
  const [slow, setSlow] = useState(false);
  const colors = themeColors(useColorScheme() === "dark");
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), SLOW_CONNECTION_MS);
    return () => clearTimeout(timer);
  }, []);
  return (
    <View className="flex-1 items-center justify-center gap-3 bg-background p-6 dark:bg-background-dark">
      <ActivityIndicator size="large" color={colors.brand} />
      {slow ? (
        <>
          <Text className="font-sans-semibold text-lg text-foreground dark:text-foreground-dark">
            Still connecting…
          </Text>
          <Text className="text-center font-sans text-sm text-muted-foreground dark:text-muted-foreground-dark">
            Check your internet connection — we&apos;ll keep trying.
          </Text>
        </>
      ) : (
        <Text className="font-sans text-sm text-muted-foreground dark:text-muted-foreground-dark">
          Loading…
        </Text>
      )}
    </View>
  );
}

function useCacheResetOnIdentityChange() {
  const { userId, orgId } = useAuth();
  const identity = `${userId ?? ""}:${orgId ?? ""}`;
  const previousIdentity = useRef(identity);

  useEffect(() => {
    if (previousIdentity.current === identity) return;
    previousIdentity.current = identity;
    queryClient.clear();
  }, [identity]);
}

function AppShell() {
  const apiContext = useApiContext();
  useCacheResetOnIdentityChange();
  return (
    <ApiProvider value={apiContext}>
      <Slot />
    </ApiProvider>
  );
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts(appFonts);
  const isDark = useColorScheme() === "dark";

  useEffect(() => {
    if (fontsLoaded || fontError) {
      void SplashScreen.hideAsync();
    }
  }, [fontsLoaded, fontError]);

  if (!fontsLoaded && !fontError) {
    return null;
  }

  return (
    <RootErrorBoundary>
      <StatusBar style="auto" />
      <ThemeProvider
        value={isDark ? darkNavigationTheme : lightNavigationTheme}
      >
        <ClerkProvider
          publishableKey={CLERK_PUBLISHABLE_KEY}
          tokenCache={tokenCache}
        >
          <ClerkLoading>
            <ClerkLoadingScreen />
          </ClerkLoading>
          <ClerkLoaded>
            <QueryClientProvider client={queryClient}>
              <GestureHandlerRootView style={{ flex: 1 }}>
                <KeyboardProvider>
                  <SafeAreaProvider>
                    <BottomSheetModalProvider>
                      <KeyboardAvoidingView
                        behavior="padding"
                        style={{ flex: 1 }}
                      >
                        <AppShell />
                      </KeyboardAvoidingView>
                      <Toaster />
                    </BottomSheetModalProvider>
                  </SafeAreaProvider>
                </KeyboardProvider>
              </GestureHandlerRootView>
            </QueryClientProvider>
          </ClerkLoaded>
        </ClerkProvider>
      </ThemeProvider>
    </RootErrorBoundary>
  );
}
