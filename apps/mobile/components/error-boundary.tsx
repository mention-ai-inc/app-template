import { Component, type ReactNode } from "react";
import { ScrollView, Text, View } from "react-native";

type Props = { children: ReactNode };
type State = { error: Error | null };

/**
 * Catches render-time errors anywhere below the root so a failure surfaces a
 * readable message instead of a blank white screen (which App Review rejects).
 */
export class RootErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    const { error } = this.state;
    if (!error) {
      return this.props.children;
    }
    return (
      <View className="flex-1 bg-background dark:bg-background-dark p-6 pt-20">
        <Text className="text-lg font-semibold text-red-600">
          Something went wrong
        </Text>
        <ScrollView className="mt-3">
          <Text className="text-sm text-foreground dark:text-foreground-dark">
            {error.message}
          </Text>
          {error.stack ? (
            <Text className="mt-4 text-xs text-muted-foreground dark:text-muted-foreground-dark">
              {error.stack}
            </Text>
          ) : null}
        </ScrollView>
      </View>
    );
  }
}
