import { useNavigate } from "react-router-dom";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useDeleteNote } from "./queries";

/**
 * Shared soft-delete confirmation dialog (D-14/D-15/D-16).
 *
 * Used by BOTH the sidebar row "⋯" menu (NoteList) and the editor header menu.
 * Controlled via `open`/`onOpenChange`. On confirm it soft-deletes the note and,
 * when the deleted note is the one currently open, routes back to the index empty
 * state ("Select or create a note", D-16).
 *
 * Copy is the EXACT UI-SPEC contract — do not reword.
 */
interface DeleteNoteDialogProps {
  noteId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** When true, navigate to the index empty state after delete (editor context, D-16). */
  navigateAfterDelete?: boolean;
}

export function DeleteNoteDialog({
  noteId,
  open,
  onOpenChange,
  navigateAfterDelete = false,
}: DeleteNoteDialogProps) {
  const navigate = useNavigate();
  const del = useDeleteNote();

  const handleDelete = () => {
    if (!noteId) return;
    del.mutate(noteId, {
      onSuccess: () => {
        onOpenChange(false);
        if (navigateAfterDelete) {
          navigate("/", { replace: true });
        }
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete this note?</DialogTitle>
          <DialogDescription>
            This note will be removed from your list.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={del.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={del.isPending}
          >
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
