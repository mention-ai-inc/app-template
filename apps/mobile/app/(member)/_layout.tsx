import { SignOutLink } from "@/components/sign-out-link";
import { themeColors } from "@/lib/theme";
import { useAuth, useOrganization } from "@clerk/clerk-expo";
import { Feather } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import { ActivityIndicator, Text, useColorScheme, View } from "react-native";

export default function MemberLayout() {
  const { isSignedIn, isLoaded, orgId } = useAuth();
  const { isLoaded: orgLoaded } = useOrganization();
  const colors = themeColors(useColorScheme() === "dark");

  if (!isLoaded || !orgLoaded) {
    return (
      <View className="flex-1 items-center justify-center bg-background dark:bg-background-dark">
        <ActivityIndicator color={colors.brand} />
      </View>
    );
  }
  if (!isSignedIn) return <Redirect href="/sign-in" />;

  if (orgId == null) {
    return (
      <View className="flex-1 items-center justify-center gap-stack bg-background px-screen dark:bg-background-dark">
        <Text className="text-center font-sans text-base text-foreground dark:text-foreground-dark">
          This account is not a member of any organization.
        </Text>
        <SignOutLink />
      </View>
    );
  }

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brand,
        tabBarInactiveTintColor: colors["muted-foreground"],
        tabBarStyle: {
          borderTopColor: colors.border,
          backgroundColor: colors.background,
        },
      }}
    >
      <Tabs.Screen
        name="notes"
        options={{
          title: "Notes",
          tabBarIcon: ({ color, size }) => (
            <Feather name="file-text" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
