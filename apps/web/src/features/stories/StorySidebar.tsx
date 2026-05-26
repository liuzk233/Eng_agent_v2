import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import type { StoryProject } from "./storyTypes";

const STYLE_LABELS: Record<StoryProject["style"], string> = {
  web_novel: "网络爽文",
  science_fiction: "科幻小说",
  exam_reading: "应试阅读",
};

interface StorySidebarProps {
  stories: StoryProject[];
  selectedStoryId: string | null;
  onSelectStory: (id: string) => void;
  onNewStory: () => void;
  onRenameStory?: (id: string, title: string) => Promise<unknown>;
  isRenaming?: boolean;
  onDeleteStory?: (id: string) => Promise<unknown>;
  isDeleting?: boolean;
  onHome?: () => void;
}

export function StorySidebar({
  stories,
  selectedStoryId,
  onSelectStory,
  onNewStory,
  onRenameStory = async () => undefined,
  isRenaming = false,
  onDeleteStory = async () => undefined,
  isDeleting = false,
  onHome = () => {},
}: StorySidebarProps) {
  const sidebarRef = useRef<HTMLElement | null>(null);
  const renameInputRef = useRef<HTMLInputElement | null>(null);
  const deleteCancelButtonRef = useRef<HTMLButtonElement | null>(null);
  const [openMenuStoryId, setOpenMenuStoryId] = useState<string | null>(null);
  const [editingStoryId, setEditingStoryId] = useState<string | null>(null);
  const [deleteDialogStory, setDeleteDialogStory] = useState<StoryProject | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [renameError, setRenameError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [savingStoryId, setSavingStoryId] = useState<string | null>(null);
  const [deletingStoryId, setDeletingStoryId] = useState<string | null>(null);
  const isDeletePending = Boolean(deletingStoryId) || isDeleting;

  useEffect(() => {
    if (editingStoryId) {
      renameInputRef.current?.focus();
      renameInputRef.current?.select();
    }
  }, [editingStoryId]);

  useEffect(() => {
    if (!openMenuStoryId) return;

    function handlePointerDown(event: PointerEvent) {
      const target = event.target;
      if (!(target instanceof Node)) return;
      const activeRow = sidebarRef.current?.querySelector(
        `[data-story-row-id="${openMenuStoryId}"]`,
      );
      if (activeRow?.contains(target)) return;
      setOpenMenuStoryId(null);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [openMenuStoryId]);

  useEffect(() => {
    if (!deleteDialogStory) return;
    deleteCancelButtonRef.current?.focus();
  }, [deleteDialogStory]);

  useEffect(() => {
    if (!deleteDialogStory) return;

    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key !== "Escape" || isDeletePending) return;
      event.preventDefault();
      closeDeleteDialog();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [deleteDialogStory, isDeletePending]);

  function startRename(story: StoryProject) {
    setOpenMenuStoryId(null);
    setEditingStoryId(story.id);
    setDraftTitle(story.title);
    setRenameError("");
  }

  function cancelRename() {
    if (savingStoryId) return;
    setEditingStoryId(null);
    setDraftTitle("");
    setRenameError("");
  }

  function startDelete(story: StoryProject) {
    setOpenMenuStoryId(null);
    setDeleteDialogStory(story);
    setDeleteError("");
  }

  function closeDeleteDialog() {
    if (isDeletePending) return;
    setDeleteDialogStory(null);
    setDeleteError("");
  }

  async function confirmDelete() {
    if (!deleteDialogStory || isDeletePending) return;

    setDeleteError("");
    setDeletingStoryId(deleteDialogStory.id);
    try {
      await onDeleteStory(deleteDialogStory.id);
      setDeleteDialogStory(null);
    } catch {
      setDeleteError("删除失败，请重试");
    } finally {
      setDeletingStoryId(null);
    }
  }

  async function handleRenameSubmit(story: StoryProject, event?: FormEvent) {
    event?.preventDefault();
    const title = draftTitle.trim();
    if (!title) {
      setRenameError("名称不能为空");
      return;
    }

    setRenameError("");
    setSavingStoryId(story.id);
    try {
      await onRenameStory(story.id, title);
      setEditingStoryId(null);
      setDraftTitle("");
    } catch {
      setRenameError("重命名失败，请重试");
    } finally {
      setSavingStoryId(null);
    }
  }

  function handleRenameKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      cancelRename();
    }
  }

  function handleRowKeyDown(event: KeyboardEvent<HTMLLIElement>) {
    if (event.key === "Escape" && openMenuStoryId) {
      event.preventDefault();
      setOpenMenuStoryId(null);
    }
  }

  return (
    <aside ref={sidebarRef} className="story-sidebar" aria-label="故事列表">
      <div className="story-sidebar-header">
        <button
          type="button"
          className="story-brand"
          onClick={onHome}
          aria-label="回到 WordFlow 主界面"
        >
          <span className="story-brand-mark" aria-hidden="true">W</span>
          <div>
            <p className="auth-kicker">Closed beta</p>
            <h1 className="text-title">WordFlow</h1>
          </div>
        </button>
        <button type="button" className="story-new-btn" onClick={onNewStory}>
          新建故事
        </button>
      </div>

      {stories.length === 0 ? (
        <div className="story-sidebar-empty">
          <p className="text-supporting">还没有故事，点击上方按钮开始创建</p>
        </div>
      ) : (
        <section className="story-history" aria-labelledby="story-history-heading">
          <h2 id="story-history-heading" className="story-history-heading text-micro-label">历史故事</h2>
          <ul className="story-sidebar-list">
            {stories.map((story) => {
              const isSelected = story.id === selectedStoryId;
              const isEditing = story.id === editingStoryId;
              const isSaving = story.id === savingStoryId || (isEditing && isRenaming);
              const errorId = `rename-story-error-${story.id}`;

              return (
                <li
                  key={story.id}
                  className={`story-sidebar-row ${isSelected ? "story-sidebar-row--selected" : ""} ${isEditing ? "story-sidebar-row--editing" : ""}`}
                  data-story-row-id={story.id}
                  onKeyDown={handleRowKeyDown}
                >
                  {isEditing ? (
                    <form
                      className="story-rename-form"
                      onSubmit={(event) => void handleRenameSubmit(story, event)}
                    >
                      <label className="story-rename-label" htmlFor={`rename-story-${story.id}`}>
                        重命名故事名称
                      </label>
                      <div className="story-rename-controls">
                        <input
                          ref={renameInputRef}
                          id={`rename-story-${story.id}`}
                          className="story-rename-input"
                          type="text"
                          value={draftTitle}
                          onChange={(event) => {
                            setDraftTitle(event.target.value);
                            if (renameError) setRenameError("");
                          }}
                          onKeyDown={handleRenameKeyDown}
                          disabled={isSaving}
                          aria-invalid={renameError ? "true" : undefined}
                          aria-describedby={renameError ? errorId : undefined}
                        />
                        <div className="story-rename-actions">
                          <button
                            type="submit"
                            className="story-rename-save"
                            disabled={isSaving}
                          >
                            {isSaving ? "保存中" : "保存"}
                          </button>
                          <button
                            type="button"
                            className="story-rename-cancel"
                            onClick={cancelRename}
                            disabled={isSaving}
                          >
                            取消
                          </button>
                        </div>
                      </div>
                      {renameError && (
                        <p id={errorId} className="story-rename-error" role="alert">
                          {renameError}
                        </p>
                      )}
                    </form>
                  ) : (
                    <>
                      <button
                        type="button"
                        className={`story-sidebar-item ${isSelected ? "story-sidebar-item--selected" : ""}`}
                        onClick={() => onSelectStory(story.id)}
                        aria-current={isSelected ? "true" : undefined}
                      >
                        <span className="story-sidebar-item-title">{story.title}</span>
                        <span className="story-sidebar-item-meta text-micro-label">
                          {STYLE_LABELS[story.style]} · {story.targetChapterCount} 章
                        </span>
                      </button>
                      <div className="story-row-actions">
                        <button
                          type="button"
                          className="story-row-menu-trigger"
                          aria-label={`打开故事操作菜单：${story.title}`}
                          aria-haspopup="menu"
                          aria-expanded={openMenuStoryId === story.id}
                          onClick={() =>
                            setOpenMenuStoryId((current) =>
                              current === story.id ? null : story.id,
                            )
                          }
                        >
                          <span aria-hidden="true">...</span>
                        </button>
                        {openMenuStoryId === story.id && (
                          <div className="story-row-menu" role="menu">
                            <button
                              type="button"
                              className="story-row-menu-item"
                              role="menuitem"
                              onClick={() => startRename(story)}
                            >
                              重命名
                            </button>
                            <button
                              type="button"
                              className="story-row-menu-item story-row-menu-item--danger"
                              role="menuitem"
                              onClick={() => startDelete(story)}
                            >
                              删除
                            </button>
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      )}
      {deleteDialogStory && (
        <div
          className="dialog-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeDeleteDialog();
            }
          }}
        >
          <div
            className="dialog-content story-delete-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-story-title"
            aria-describedby="delete-story-description"
          >
            <h2 id="delete-story-title" className="text-subtitle">删除故事</h2>
            <p id="delete-story-description" className="text-body">
              确定删除「<span>{deleteDialogStory.title}</span>」吗？
            </p>
            {deleteError && (
              <p className="story-delete-error" role="alert">
                {deleteError}
              </p>
            )}
            <div className="dialog-actions">
              <button
                ref={deleteCancelButtonRef}
                type="button"
                className="dialog-cancel-btn"
                onClick={closeDeleteDialog}
                disabled={isDeletePending}
              >
                取消
              </button>
              <button
                type="button"
                className="story-delete-confirm-btn"
                onClick={() => void confirmDelete()}
                disabled={isDeletePending}
              >
                {isDeletePending ? "删除中" : "确认删除"}
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
