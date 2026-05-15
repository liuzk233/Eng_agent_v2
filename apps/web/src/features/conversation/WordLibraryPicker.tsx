import { useState } from "react";

interface WordLibraryPickerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (word: string) => void;
  selectedWords: Set<string>;
  availableWords?: string[];
}

const DEFAULT_WORDS = [
  "abandon", "ability", "absent", "absorb", "abstract",
  "academic", "accept", "access", "accomplish", "accurate",
  "achieve", "acknowledge", "adapt", "adequate", "adjust",
];

export function WordLibraryPicker({
  open,
  onClose,
  onSelect,
  selectedWords,
  availableWords = DEFAULT_WORDS,
}: WordLibraryPickerProps) {
  const [search, setSearch] = useState("");

  if (!open) return null;

  const filtered = availableWords.filter(
    (w) => w.toLowerCase().includes(search.toLowerCase()) && !selectedWords.has(w),
  );

  return (
    <div className="dialog-overlay" role="dialog" aria-modal="true" aria-label="从词库选择">
      <div className="dialog-content word-library-picker">
        <h2 className="text-title">从词库选择</h2>
        <div className="auth-field">
          <label htmlFor="word-search">搜索词汇</label>
          <input
            id="word-search"
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <ul className="word-library-list">
          {filtered.map((word) => (
            <li key={word}>
              <button
                type="button"
                className="word-library-item"
                onClick={() => onSelect(word)}
              >
                {word}
              </button>
            </li>
          ))}
          {filtered.length === 0 && (
            <li className="text-supporting">未找到匹配词汇</li>
          )}
        </ul>
        <button type="button" className="dialog-cancel-btn" onClick={onClose}>
          关闭
        </button>
      </div>
    </div>
  );
}
