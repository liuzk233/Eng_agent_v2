interface UserWordsCardProps {
  words: string[];
}

export function UserWordsCard({ words }: UserWordsCardProps) {
  return (
    <div className="conversation-card user-words-card">
      <h4 className="text-label">目标词</h4>
      <div className="word-chips">
        {words.map((word) => (
          <span key={word} className="word-chip">{word}</span>
        ))}
      </div>
    </div>
  );
}
