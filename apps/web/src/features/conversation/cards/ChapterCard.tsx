interface ChapterCardProps {
  englishContent: string;
  highlightedTargetWords: string[];
  chineseTranslation: string;
}

export function ChapterCard({
  englishContent,
  highlightedTargetWords,
  chineseTranslation,
}: ChapterCardProps) {
  const renderedContent = highlightWords(englishContent, highlightedTargetWords);

  return (
    <div className="conversation-card chapter-card">
      <div className="chapter-english text-reading" lang="en">
        {renderedContent}
      </div>
      <div className="chapter-chinese text-body" lang="zh-CN">
        {chineseTranslation}
      </div>
    </div>
  );
}

function highlightWords(content: string, words: string[]): React.ReactNode[] {
  if (words.length === 0) return [content];

  const escaped = words.map(escapeRegex);
  const pattern = new RegExp(
    `\\*\\*(${escaped.join("|")})\\*\\*`,
    "gi",
  );

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  let match: RegExpExecArray | null;
  while ((match = pattern.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }
    parts.push(
      <mark key={key++} className="chapter-highlight">{match[1]}</mark>,
    );
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [content];
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
