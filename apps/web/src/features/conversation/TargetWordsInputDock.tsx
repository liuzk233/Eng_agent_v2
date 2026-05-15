import { useState, useCallback } from "react";
import { TargetWordChip } from "./TargetWordChip";
import { WordLibraryPicker } from "./WordLibraryPicker";

const MAX_WORDS = 10;

interface TargetWordsInputDockProps {
  words: string[];
  onWordsChange: (words: string[]) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

export function TargetWordsInputDock({
  words,
  onWordsChange,
  onSubmit,
  disabled = false,
}: TargetWordsInputDockProps) {
  const [inputValue, setInputValue] = useState("");
  const [libraryOpen, setLibraryOpen] = useState(false);
  const isAtLimit = words.length >= MAX_WORDS;

  const addWords = useCallback(
    (raw: string) => {
      const parsed = raw
        .split(/[,，\s\n]+/)
        .map((w) => w.trim().toLowerCase())
        .filter((w) => w.length > 0);

      const newWords: string[] = [];
      for (const w of parsed) {
        if (words.includes(w) || newWords.includes(w)) continue;
        if (words.length + newWords.length >= MAX_WORDS) break;
        newWords.push(w);
      }
      if (newWords.length > 0) {
        onWordsChange([...words, ...newWords]);
      }
    },
    [words, onWordsChange],
  );

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && inputValue.trim()) {
      e.preventDefault();
      addWords(inputValue);
      setInputValue("");
    }
  }

  function handlePaste(e: React.ClipboardEvent<HTMLInputElement>) {
    const pasted = e.clipboardData.getData("text");
    if (pasted.includes(",") || pasted.includes("\n") || pasted.includes("，")) {
      e.preventDefault();
      addWords(pasted);
      setInputValue("");
    }
  }

  function removeWord(word: string) {
    onWordsChange(words.filter((w) => w !== word));
  }

  function handleLibrarySelect(word: string) {
    if (!words.includes(word) && words.length < MAX_WORDS) {
      onWordsChange([...words, word]);
    }
  }

  return (
    <div className="target-words-dock">
      <div className="target-words-dock-header">
        <label htmlFor="target-word-input" className="text-label">
          目标词
        </label>
        <span className="text-micro-label">
          {words.length}/{MAX_WORDS}
        </span>
      </div>

      <div className="target-words-chips">
        {words.map((word) => (
          <TargetWordChip
            key={word}
            word={word}
            onRemove={() => removeWord(word)}
            disabled={disabled}
          />
        ))}
      </div>

      {isAtLimit && !disabled && (
        <p className="target-words-warning text-supporting">
          已达上限（{MAX_WORDS} 个词）
        </p>
      )}

      {!disabled && (
        <div className="target-words-input-row">
          <input
            id="target-word-input"
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            disabled={isAtLimit}
            placeholder="输入单词后按 Enter 添加"
          />
          <button
            type="button"
            className="word-library-btn"
            onClick={() => setLibraryOpen(true)}
            disabled={isAtLimit}
          >
            从词库选择
          </button>
          <button
            type="button"
            className="auth-submit"
            onClick={onSubmit}
            disabled={words.length === 0}
          >
            确认目标词
          </button>
        </div>
      )}

      <WordLibraryPicker
        open={libraryOpen}
        onClose={() => setLibraryOpen(false)}
        onSelect={handleLibrarySelect}
        selectedWords={new Set(words)}
      />
    </div>
  );
}
