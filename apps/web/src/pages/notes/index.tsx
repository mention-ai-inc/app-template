import type { components } from "@packages/acme-api";
import { useCreateNote, useNotes } from "@packages/acme-api-client";
import { OrganizationSwitcher, UserButton } from "@clerk/react";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorComponent } from "@/components/page-states/error";
import { PageLoading } from "@/components/page-states/loading";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { getErrorMessage } from "@/lib/utils";

export function NotesPage() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 p-6">
      <header className="flex items-center justify-between">
        <h1 className="font-serif text-3xl tracking-tight">Notes</h1>
        <div className="flex items-center gap-3">
          <OrganizationSwitcher hidePersonal />
          <UserButton />
        </div>
      </header>
      <CreateNoteForm />
      <NoteList />
    </div>
  );
}

function CreateNoteForm() {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const createNote = useCreateNote();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createNote.mutate(
      { title: title.trim(), body: body.trim() },
      {
        onSuccess: () => {
          setTitle("");
          setBody("");
        },
        onError: (error) =>
          toast.error(getErrorMessage(error, "Could not save the note")),
      },
    );
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="title">Title</Label>
        <Input
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          disabled={createNote.isPending}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="body">Body</Label>
        <Textarea
          id="body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={5}
          required
          disabled={createNote.isPending}
        />
      </div>
      <Button
        type="submit"
        className="self-end"
        disabled={!title.trim() || !body.trim() || createNote.isPending}
        loading={createNote.isPending}
      >
        Save note
      </Button>
    </form>
  );
}

function NoteList() {
  const notes = useNotes();

  if (notes.isPending) {
    return <PageLoading />;
  }
  if (notes.isError) {
    return <ErrorComponent error={notes.error} />;
  }
  if (notes.data.notes.length === 0) {
    return <p className="text-sm text-muted-foreground">No notes yet.</p>;
  }

  return (
    <ul className="flex flex-col gap-4">
      {notes.data.notes.map((note) => (
        <NoteItem key={note.id} note={note} />
      ))}
    </ul>
  );
}

const STATUS_LABEL: Record<components["schemas"]["NoteStatus"], string> = {
  pending: "Waiting to be summarized",
  summarizing: "Being summarized",
  summarized: "Summarized",
};

function NoteItem({ note }: { note: components["schemas"]["NoteRead"] }) {
  return (
    <li className="flex flex-col gap-2 rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-medium">{note.title}</h2>
        <Badge variant={note.status === "summarized" ? "success" : "warning"}>
          {STATUS_LABEL[note.status]}
        </Badge>
      </div>
      {note.summary !== null && <p className="text-sm">{note.summary}</p>}
      <time
        dateTime={note.created_at}
        className="text-xs text-muted-foreground"
      >
        {new Date(note.created_at).toLocaleString()}
      </time>
    </li>
  );
}
