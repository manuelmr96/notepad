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

// Shared soft-delete confirmation dialog (D-14/D-15/D-16): used by both the sidebar row menu and the editor header; on confirm soft-deletes and, when the open note is deleted, routes to the empty state. Copy is the EXACT UI-SPEC contract.
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
