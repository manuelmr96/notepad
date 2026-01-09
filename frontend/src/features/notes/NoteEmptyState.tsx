/**
 * Editor-pane empty state (D-16): shown at the app index route (no note selected)
 * and after deleting the open note. Muted, centered, minimal per UI-SPEC.
 */
export function NoteEmptyState() {
  return (
    <div className="flex flex-1 items-center justify-center p-12">
      <p className="text-sm text-muted-foreground">Select or create a note</p>
    </div>
  );
}
