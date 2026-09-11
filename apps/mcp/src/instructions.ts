const INSTRUCTIONS =
  "You are connected to Acme, this organization's notes. Each note has a title, a body, and a summary that Acme writes shortly after the note is created; a note whose status is pending or summarizing has no summary yet. " +
  "Call list_notes to see every note in the organization, and create_note to record a new one.";

export function buildInstructions(): string {
  return INSTRUCTIONS;
}
