import { useCallback, useEffect, useMemo, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { type Note, type NoteUpdate, noteKey, notesKey } from "./queries";

/**
 * NOTE-06 autosave: a debounced, optimistic PATCH against /notes/:id.
 *
 * Implements RESEARCH Pattern 6 exactly:
 *   onMutate  -> cancelQueries(["notes", id]); snapshot; optimistic setQueryData
 *   onError   -> rollback to the snapshot
 *   onSettled -> invalidate ["notes", id] AND ["notes"] (so the sidebar reorders
 *                by updated_at)
 *
 * Edits are debounced (~D-07 1-2s) and FLUSHED immediately on input blur, route
 * change, and `window` `beforeunload` so nothing is ever lost (Pitfall 5).
 *
 * `status` maps to the UI-SPEC copy: "saving" -> "Saving…", "saved" -> "Saved",
 * "error" -> the destructive autosave-failure copy (D-08).
 */

export type AutosaveStatus = "idle" | "saving" | "saved" | "error";

/** Default debounce window for autosave (D-07: ~1-2s after typing stops). */
export const AUTOSAVE_DEBOUNCE_MS = 1200;

/** ~10-line debounced callback: clears the prior timer on each call; exposes cancel/flush. */
function useDebouncedCallback<A extends unknown[]>(
  fn: (...args: A) => void,
  ms: number,
) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef<A | null>(null);
  // Keep the freshest fn without resetting the timer.
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const cancel = useCallback(() => {
    if (timer.current !== null) {
      clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  const schedule = useCallback(
    (...args: A) => {
      latest.current = args;
      cancel();
      timer.current = setTimeout(() => {
        timer.current = null;
        if (latest.current) fnRef.current(...latest.current);
      }, ms);
    },
    [cancel, ms],
  );

  const flush = useCallback(() => {
    if (timer.current !== null) {
      cancel();
      if (latest.current) fnRef.current(...latest.current);
    }
  }, [cancel]);

  // Clear any pending timer on unmount so a dangling save can't fire late.
  useEffect(() => cancel, [cancel]);

  return { schedule, flush, cancel };
}

interface AutosaveResult {
  /** Schedule a debounced optimistic save with the latest patch. */
  onChange: (patch: NoteUpdate) => void;
  /** Fire any pending save immediately (blur / route change / unload). */
  flush: () => void;
  /** Current UI status derived from the mutation (D-08). */
  status: AutosaveStatus;
}

export function useAutosave(
  noteId: string | undefined,
  debounceMs: number = AUTOSAVE_DEBOUNCE_MS,
): AutosaveResult {
  const qc = useQueryClient();

  const save = useMutation<Note, Error, NoteUpdate, { prev: Note | undefined }>({
    mutationFn: async (patch: NoteUpdate) => {
      const res = await apiFetch(`/notes/${noteId}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      if (!res.ok) {
        throw new Error(`Autosave failed with status ${res.status}`);
      }
      return (await res.json()) as Note;
    },
    // Pattern 6 / Pitfall 4: cancel in-flight refetches, snapshot, optimistic write.
    onMutate: async (patch) => {
      if (!noteId) return { prev: undefined };
      await qc.cancelQueries({ queryKey: noteKey(noteId) });
      const prev = qc.getQueryData<Note>(noteKey(noteId));
      if (prev) {
        qc.setQueryData<Note>(noteKey(noteId), { ...prev, ...patch });
      }
      return { prev };
    },
    onError: (_err, _patch, ctx) => {
      if (noteId && ctx?.prev) {
        qc.setQueryData(noteKey(noteId), ctx.prev);
      }
    },
    // Pattern 6: invalidate only on settle — the single note AND the list (so the
    // sidebar reorders by updated_at).
    onSettled: () => {
      if (!noteId) return;
      void qc.invalidateQueries({ queryKey: noteKey(noteId) });
      void qc.invalidateQueries({ queryKey: notesKey });
    },
  });

  const { mutate } = save;
  const doSave = useCallback(
    (patch: NoteUpdate) => {
      if (noteId) mutate(patch);
    },
    [mutate, noteId],
  );

  const { schedule, flush, cancel } = useDebouncedCallback(doSave, debounceMs);

  // Flush on tab close / refresh so in-flight edits are not lost (Pitfall 5, D-07).
  useEffect(() => {
    const onBeforeUnload = () => flush();
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
    };
  }, [flush]);

  // Flush pending edits when the active note changes (route change between notes).
  useEffect(() => {
    return () => {
      flush();
    };
  }, [noteId, flush]);

  // Reset the debounce timer when switching notes so a stale patch can't target
  // the wrong note.
  useEffect(() => {
    return cancel;
  }, [noteId, cancel]);

  const status: AutosaveStatus = useMemo(() => {
    if (save.isError) return "error";
    if (save.isPending) return "saving";
    if (save.isSuccess) return "saved";
    return "idle";
  }, [save.isError, save.isPending, save.isSuccess]);

  return { onChange: schedule, flush, status };
}
