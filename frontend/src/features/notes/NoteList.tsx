import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { MoreHorizontal, Plus } from "lucide-react";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useCreateNote, useNotes } from "./queries";
import { DeleteNoteDialog } from "./DeleteNoteDialog";

/** Compact relative-time formatter ("just now" / "2h ago" / "3d ago"). */
function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks}w ago`;
  return new Date(iso).toLocaleDateString();
}

// Sidebar note list (NOTE-02): New-note button (D-05), rows with title + relative updated time and a per-row delete menu (D-15), skeleton loading, exact empty-state copy; selecting a row routes to /notes/:id and closes the mobile drawer.
export function NoteList() {
  const navigate = useNavigate();
  const { id: activeId } = useParams();
  const { setOpenMobile, isMobile } = useSidebar();
  const { data: notes, isPending } = useNotes();
  const createNote = useCreateNote();

  const [deleteId, setDeleteId] = useState<string | null>(null);

  const closeDrawer = () => {
    if (isMobile) setOpenMobile(false);
  };

  const handleNew = () => {
    createNote.mutate(
      {},
      {
        onSuccess: (note) => {
          closeDrawer();
          navigate(`/notes/${note.id}`);
        },
      },
    );
  };

  const openNote = (noteId: string) => {
    closeDrawer();
    navigate(`/notes/${noteId}`);
  };

  return (
    <>
      <SidebarHeader className="flex-row items-center justify-between gap-2 px-3 py-3">
        <span className="text-sm font-semibold">Notes</span>
        <Button
          size="sm"
          variant="ghost"
          className="gap-1"
          onClick={handleNew}
          disabled={createNote.isPending}
        >
          <Plus className="size-4" aria-hidden="true" />
          New note
        </Button>
      </SidebarHeader>

      <SidebarGroup className="flex-1 overflow-y-auto">
        <SidebarGroupContent>
          {isPending ? (
            <SidebarMenu>
              {Array.from({ length: 5 }).map((_, i) => (
                <SidebarMenuItem key={i}>
                  <SidebarMenuSkeleton showIcon={false} />
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          ) : notes && notes.length > 0 ? (
            <SidebarMenu>
              {notes.map((note) => {
                const isActive = note.id === activeId;
                return (
                  <SidebarMenuItem key={note.id} className="group/row">
                    <SidebarMenuButton
                      isActive={isActive}
                      onClick={() => openNote(note.id)}
                      className={cn(
                        "h-auto flex-col items-start gap-0.5 py-2",
                        isActive && "border-l-2 border-primary",
                      )}
                    >
                      <span className="w-full truncate text-base">
                        {note.title.trim() || "Untitled"}
                      </span>
                      <span className="text-sm text-muted-foreground">
                        {relativeTime(note.updated_at)}
                      </span>
                    </SidebarMenuButton>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button
                          type="button"
                          aria-label="Note options"
                          className="absolute right-1 top-1.5 flex size-11 items-center justify-center rounded-md text-muted-foreground opacity-0 hover:bg-sidebar-accent focus-visible:opacity-100 group-hover/row:opacity-100 sm:size-8"
                        >
                          <MoreHorizontal className="size-4" aria-hidden="true" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent side="right" align="start">
                        <DropdownMenuItem
                          variant="destructive"
                          onSelect={() => setDeleteId(note.id)}
                        >
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          ) : (
            <div className="flex flex-col items-center gap-3 px-4 py-12 text-center">
              <p className="text-xl font-semibold">No notes yet</p>
              <p className="text-sm text-muted-foreground">
                Create your first note to get started.
              </p>
              <Button
                size="sm"
                className="gap-1"
                onClick={handleNew}
                disabled={createNote.isPending}
              >
                <Plus className="size-4" aria-hidden="true" />
                New note
              </Button>
            </div>
          )}
        </SidebarGroupContent>
      </SidebarGroup>

      <DeleteNoteDialog
        noteId={deleteId}
        open={deleteId !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteId(null);
        }}
        navigateAfterDelete={deleteId === activeId}
      />
    </>
  );
}
