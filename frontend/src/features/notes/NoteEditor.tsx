import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { MoreHorizontal } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { useNote, type NoteContent } from "./queries";
import { useAutosave } from "./useAutosave";
import { DeleteNoteDialog } from "./DeleteNoteDialog";

/**
 * Phase-1 content JSON contract (CONTEXT.md / D-06): the body is plain text
 * wrapped as an editor-native ProseMirror-style doc and persisted in
 * `content JSONB` (content_schema_version=1, set server-side). NOT raw markdown
 * TEXT — Phase 2/5 upgrades the schema version, not the column type.
 */
function bodyToContent(body: string): NoteContent {
  return {
    type: "doc",
    content: body
      ? [{ type: "paragraph", content: [{ type: "text", text: body }] }]
      : [{ type: "paragraph" }],
  };
}

/** Extract the plain body text back out of the stored content doc. */
function contentToBody(content: NoteContent | null): string {
  if (!content || !Array.isArray(content.content)) return "";
  const parts: string[] = [];
  for (const block of content.content as Array<Record<string, unknown>>) {
    const inner = block?.content;
    if (Array.isArray(inner)) {
      for (const node of inner as Array<Record<string, unknown>>) {
        if (typeof node?.text === "string") parts.push(node.text);
      }
    }
  }
  return parts.join("\n");
}

/**
 * NoteEditor (NOTE-03/04/06, D-06/07/08): a Display-weight title input + a
 * minimal multi-line body surface. Edits schedule a debounced optimistic
 * autosave; the muted status reads "Saving…" / "Saved" (or the destructive
 * failure copy). Flushes on blur. A header "⋯" menu opens the shared
 * delete-confirm dialog, which soft-deletes and routes to the empty state (D-16).
 */
export function NoteEditor() {
  const { id } = useParams();
  const { data: note, isPending } = useNote(id);
  const { onChange, flush, status } = useAutosave(id);

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);
  // Track which note id the local draft reflects so we re-seed on note switch.
  const loadedId = useRef<string | undefined>(undefined);

  // Seed local draft from the loaded note (once per note).
  useEffect(() => {
    if (note && loadedId.current !== note.id) {
      setTitle(note.title);
      setBody(contentToBody(note.content));
      loadedId.current = note.id;
      // Autofocus the title for a freshly created (empty) note (D-05).
      if (!note.title && contentToBody(note.content) === "") {
        titleRef.current?.focus();
      }
    }
  }, [note]);

  const handleTitleChange = (value: string) => {
    setTitle(value);
    onChange({ title: value });
  };

  const handleBodyChange = (value: string) => {
    setBody(value);
    onChange({ content: bodyToContent(value) });
  };

  if (isPending) {
    return (
      <div className="mx-auto w-full max-w-3xl flex-1 space-y-4 px-4 py-8 sm:px-6">
        <Skeleton className="h-9 w-2/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    );
  }

  if (!note) {
    return (
      <div className="flex flex-1 items-center justify-center p-12">
        <p className="text-sm text-muted-foreground">Select or create a note</p>
      </div>
    );
  }

  const statusLabel =
    status === "saving"
      ? "Saving…"
      : status === "saved"
        ? "Saved"
        : status === "error"
          ? "Couldn't save. We'll retry — your changes are kept locally."
          : "";

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-8 sm:px-6">
        <div className="mb-2 flex items-start gap-2">
          <input
            ref={titleRef}
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            onBlur={() => flush()}
            placeholder="Untitled"
            aria-label="Note title"
            className="min-w-0 flex-1 bg-transparent text-[28px] font-semibold leading-tight outline-none placeholder:text-muted-foreground/60"
          />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                aria-label="Note options"
                className="flex size-11 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted sm:size-9"
              >
                <MoreHorizontal className="size-5" aria-hidden="true" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                variant="destructive"
                onSelect={() => setDeleteOpen(true)}
              >
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <p className="mb-4 h-5 text-sm text-muted-foreground aria-[invalid]:text-destructive" data-status={status}>
          <span className={status === "error" ? "text-destructive" : undefined}>
            {statusLabel}
          </span>
        </p>

        <textarea
          value={body}
          onChange={(e) => handleBodyChange(e.target.value)}
          onBlur={() => flush()}
          placeholder="Start writing…"
          aria-label="Note body"
          className="flex-1 resize-none bg-transparent text-base leading-relaxed outline-none placeholder:text-muted-foreground/60"
        />
      </div>

      <DeleteNoteDialog
        noteId={note.id}
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        navigateAfterDelete
      />
    </div>
  );
}
