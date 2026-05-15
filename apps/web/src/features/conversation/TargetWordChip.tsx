interface TargetWordChipProps {
  word: string;
  onRemove: () => void;
  disabled?: boolean;
}

export function TargetWordChip({ word, onRemove, disabled }: TargetWordChipProps) {
  return (
    <span className="target-word-chip">
      {word}
      {!disabled && (
        <button
          type="button"
          className="target-word-chip-remove"
          onClick={onRemove}
          aria-label={`移除 ${word}`}
        >
          ×
        </button>
      )}
    </span>
  );
}
