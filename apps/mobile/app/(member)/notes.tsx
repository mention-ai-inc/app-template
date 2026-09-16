import {
  Button,
  EmptyState,
  Field,
  LoadingState,
  PageHeader,
  Surface,
} from "@/components/ui";
import { getErrorMessage } from "@/lib/errors";
import type { components } from "@packages/acme-api";
import { useCreateNote, useNotes } from "@packages/acme-api-client";
import { useState } from "react";
import { FlatList, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { toast } from "sonner-native";

const STATUS_LABELS: Record<components["schemas"]["NoteStatus"], string> = {
  pending: "Waiting to be summarized",
  summarizing: "Being summarized",
  summarized: "Summarized",
};

export default function NotesScreen() {
  const notesQuery = useNotes();

  if (notesQuery.isPending) {
    return <LoadingState />;
  }

  return (
    <SafeAreaView
      className="flex-1 bg-background dark:bg-background-dark"
      edges={["top"]}
    >
      <PageHeader title="Notes" />
      <FlatList
        data={notesQuery.data?.notes ?? []}
        keyExtractor={(note) => note.id}
        contentContainerClassName="flex-grow gap-stack px-screen py-6"
        keyboardShouldPersistTaps="handled"
        refreshing={notesQuery.isRefetching}
        onRefresh={() => void notesQuery.refetch()}
        ListHeaderComponent={<CreateNoteForm />}
        ListEmptyComponent={
          notesQuery.isError ? (
            <View className="items-center gap-stack py-16">
              <Text className="text-center text-base text-muted-foreground dark:text-muted-foreground-dark">
                {getErrorMessage(notesQuery.error, "Could not load notes.")}
              </Text>
              <Button
                label="Try again"
                variant="secondary"
                onPress={() => void notesQuery.refetch()}
              />
            </View>
          ) : (
            <EmptyState icon="file-text" title="No notes yet" />
          )
        }
        renderItem={({ item }) => <NoteCard note={item} />}
      />
    </SafeAreaView>
  );
}

function CreateNoteForm() {
  const createNote = useCreateNote();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  const onSubmit = () => {
    createNote.mutate(
      { title: title.trim(), body: body.trim() },
      {
        onSuccess: () => {
          setTitle("");
          setBody("");
        },
        onError: (error) => {
          toast.error(getErrorMessage(error, "Could not create the note."));
        },
      },
    );
  };

  return (
    <Surface className="gap-stack">
      <Field
        label="Title"
        accessibilityLabel="Title"
        value={title}
        onChangeText={setTitle}
      />
      <Field
        label="Body"
        accessibilityLabel="Body"
        multiline
        textAlignVertical="top"
        value={body}
        onChangeText={setBody}
      />
      <Button
        label="Add note"
        pendingLabel="Adding…"
        pending={createNote.isPending}
        disabled={!title.trim() || !body.trim()}
        onPress={onSubmit}
      />
    </Surface>
  );
}

function NoteCard({ note }: { note: components["schemas"]["NoteRead"] }) {
  return (
    <Surface className="gap-tight">
      <Text className="font-semibold text-lg text-foreground dark:text-foreground-dark">
        {note.title}
      </Text>
      <Text className="text-sm text-muted-foreground dark:text-muted-foreground-dark">
        {STATUS_LABELS[note.status]}
      </Text>
      {note.summary !== null ? (
        <Text className="text-base leading-6 text-foreground dark:text-foreground-dark">
          {note.summary}
        </Text>
      ) : null}
    </Surface>
  );
}
