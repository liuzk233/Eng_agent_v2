import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AppShell } from "../AppShell";
import { ConversationView } from "../ConversationView";
import { SetupCard } from "../cards/SetupCard";
import { UserWordsCard } from "../cards/UserWordsCard";
import { ChapterCard } from "../cards/ChapterCard";
import { ReviewCard } from "../cards/ReviewCard";

describe("AppShell", () => {
  it("renders sidebar and main content areas", () => {
    render(
      <AppShell
        sidebar={<div data-testid="sidebar">Sidebar</div>}
        main={<div data-testid="main">Main</div>}
      />,
    );
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("main")).toBeInTheDocument();
  });
});

describe("SetupCard", () => {
  it("renders story setup info", () => {
    render(<SetupCard title="Test Story" style="web_novel" targetChapterCount={5} />);
    expect(screen.getByText("Test Story")).toBeInTheDocument();
    expect(screen.getByText(/网络爽文/)).toBeInTheDocument();
    expect(screen.getByText(/5 章/)).toBeInTheDocument();
  });
});

describe("UserWordsCard", () => {
  it("renders target words as chips", () => {
    render(<UserWordsCard words={["adventure", "courage"]} />);
    expect(screen.getByText("adventure")).toBeInTheDocument();
    expect(screen.getByText("courage")).toBeInTheDocument();
  });
});

describe("ChapterCard", () => {
  it("renders English content and Chinese translation", () => {
    render(
      <ChapterCard
        englishContent="Lily went on an **adventure**."
        highlightedTargetWords={["adventure"]}
        chineseTranslation="Lily去冒险了。"
      />,
    );
    expect(screen.getByText("Lily去冒险了。")).toBeInTheDocument();
  });

  it("highlights target words", () => {
    render(
      <ChapterCard
        englishContent="She showed great **courage** in the **adventure**."
        highlightedTargetWords={["courage", "adventure"]}
        chineseTranslation="翻译"
      />,
    );
    const marks = document.querySelectorAll(".chapter-highlight");
    expect(marks.length).toBeGreaterThanOrEqual(1);
  });

  it("renders Chinese translation", () => {
    render(
      <ChapterCard
        englishContent="Some English text."
        highlightedTargetWords={[]}
        chineseTranslation="一些中文翻译。"
      />,
    );
    expect(screen.getByText("一些中文翻译。")).toBeInTheDocument();
  });
});

describe("ReviewCard", () => {
  it("shows out-of-syllabus rate", () => {
    render(<ReviewCard outOfSyllabusRate={0.005} retryCount={0} status="completed" />);
    expect(screen.getByText(/0.5%/)).toBeInTheDocument();
  });

  it("shows retry count when > 0", () => {
    render(<ReviewCard outOfSyllabusRate={0.01} retryCount={2} status="completed" />);
    expect(screen.getByText(/重试次数：2/)).toBeInTheDocument();
  });

  it("shows fallback_completed with correct message", () => {
    render(
      <ReviewCard
        outOfSyllabusRate={0.015}
        retryCount={3}
        status="fallback_completed"
      />,
    );
    expect(screen.getByText("已标注少量超纲词")).toBeInTheDocument();
  });

  it("shows completed status", () => {
    render(<ReviewCard outOfSyllabusRate={0.001} retryCount={0} status="completed" />);
    expect(screen.getByText("生成通过")).toBeInTheDocument();
  });
});
