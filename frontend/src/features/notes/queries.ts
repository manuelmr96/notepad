import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

// TanStack Query layer for the /notes API (Plan 05): keys ["notes"] (list) and ["notes", id]; all server state lives here, mutations invalidate to keep sidebar+editor in sync; the optimistic autosave PATCH lives in useAutosave.ts.

/** Phase-1 editor-native content document stored in `content JSONB` (D-06, CONTEXT.md). */
export interface NoteContent {
  type: "doc";
  content: unknown[];
}

/** Mirrors the backend NoteRead schema (Plan 05). */
export interface Note {
  id: string;
  title: string;
  content: NoteContent | null;
  content_schema_version: number;
  created_at: string;
  updated_at: string;
}

/** Partial autosave/update body (Plan 05 NoteUpdate — both fields optional). */
export interface NoteUpdate {
  title?: string;
  content?: NoteContent;
}

/** New-note body (Plan 05 NoteCreate — both fields optional). */
export interface NoteCreate {
  title?: string;
  content?: NoteContent;
}

export const notesKey = ["notes"] as const;
export const noteKey = (id: string) => ["notes", id] as const;

/** Parse a JSON response, throwing a descriptive error on non-2xx. */
async function readJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`Request failed with status ${res.status}`);
  }
  return (await res.json()) as T;
}

/** List the current user's notes (NOTE-02). Server sorts updated_at DESC. */
export function useNotes() {
  return useQuery({
    queryKey: notesKey,
    queryFn: async () => {
      const res = await apiFetch("/notes");
      return readJson<Note[]>(res);
    },
  });
}

/** Load a single note by id (NOTE-03). Enabled only when an id is present. */
export function useNote(id: string | undefined) {
  return useQuery({
    queryKey: noteKey(id ?? ""),
    enabled: Boolean(id),
    queryFn: async () => {
      const res = await apiFetch(`/notes/${id}`);
      return readJson<Note>(res);
    },
  });
}

// Create a note (NOTE-01, D-05 frictionless new-note): invalidates the list on success and returns the created note so the caller can navigate + focus.
export function useCreateNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: NoteCreate = {}) => {
      const res = await apiFetch("/notes", {
        method: "POST",
        body: JSON.stringify(body),
      });
      return readJson<Note>(res);
    },
    onSuccess: (note) => {
      // Seed the single-note cache so the editor renders instantly, then refresh the list so the new row appears at the top.
      qc.setQueryData(noteKey(note.id), note);
      void qc.invalidateQueries({ queryKey: notesKey });
    },
  });
}

/** Soft-delete a note (NOTE-05, D-13). Invalidates the list on success. */
export function useDeleteNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await apiFetch(`/notes/${id}`, { method: "DELETE" });
      if (!res.ok) {
        throw new Error(`Delete failed with status ${res.status}`);
      }
      return id;
    },
    onSuccess: (id) => {
      qc.removeQueries({ queryKey: noteKey(id) });
      void qc.invalidateQueries({ queryKey: notesKey });
    },
  });
}
