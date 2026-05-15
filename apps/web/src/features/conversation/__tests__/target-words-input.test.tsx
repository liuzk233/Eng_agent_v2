import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TargetWordsInputDock } from "../TargetWordsInputDock";
import { TargetWordChip } from "../TargetWordChip";

describe("TargetWordsInputDock", () => {
  it("renders input with visible label", () => {
    render(
      <TargetWordsInputDock
        words={[]}
        onWordsChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("目标词")).toBeInTheDocument();
  });

  it("can add a word by typing and pressing Enter", () => {
    const onChange = vi.fn();
    render(
      <TargetWordsInputDock
        words={[]}
        onWordsChange={onChange}
        onSubmit={vi.fn()}
      />,
    );
    const input = screen.getByPlaceholderText("输入单词后按 Enter 添加");
    fireEvent.change(input, { target: { value: "adventure" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(["adventure"]);
  });

  it("parses pasted text with commas", () => {
    const onChange = vi.fn();
    render(
      <TargetWordsInputDock
        words={[]}
        onWordsChange={onChange}
        onSubmit={vi.fn()}
      />,
    );
    const input = screen.getByPlaceholderText("输入单词后按 Enter 添加");
    fireEvent.paste(input, {
      clipboardData: { getData: () => "adventure, courage, explore" },
    });
    expect(onChange).toHaveBeenCalledWith(["adventure", "courage", "explore"]);
  });

  it("shows warning at 10 word limit", () => {
    const words = Array.from({ length: 10 }, (_, i) => `word${i}`);
    render(
      <TargetWordsInputDock
        words={words}
        onWordsChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByText(/已达上限/)).toBeInTheDocument();
  });

  it("disables input when disabled prop is true", () => {
    render(
      <TargetWordsInputDock
        words={["adventure"]}
        onWordsChange={vi.fn()}
        onSubmit={vi.fn()}
        disabled={true}
      />,
    );
    expect(screen.queryByPlaceholderText("输入单词后按 Enter 添加")).not.toBeInTheDocument();
  });

  it("existing chips remain visible when disabled", () => {
    render(
      <TargetWordsInputDock
        words={["adventure", "courage"]}
        onWordsChange={vi.fn()}
        onSubmit={vi.fn()}
        disabled={true}
      />,
    );
    expect(screen.getByText("adventure")).toBeInTheDocument();
    expect(screen.getByText("courage")).toBeInTheDocument();
  });

  it("has word library picker button", () => {
    render(
      <TargetWordsInputDock
        words={[]}
        onWordsChange={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByText("从词库选择")).toBeInTheDocument();
  });

  it("can remove a word by clicking chip remove button", () => {
    const onChange = vi.fn();
    render(
      <TargetWordsInputDock
        words={["adventure", "courage"]}
        onWordsChange={onChange}
        onSubmit={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByLabelText("移除 adventure"));
    expect(onChange).toHaveBeenCalledWith(["courage"]);
  });
});

describe("TargetWordChip", () => {
  it("renders word text", () => {
    render(<TargetWordChip word="adventure" onRemove={vi.fn()} />);
    expect(screen.getByText("adventure")).toBeInTheDocument();
  });

  it("shows remove button when not disabled", () => {
    render(<TargetWordChip word="adventure" onRemove={vi.fn()} />);
    expect(screen.getByLabelText("移除 adventure")).toBeInTheDocument();
  });

  it("hides remove button when disabled", () => {
    render(<TargetWordChip word="adventure" onRemove={vi.fn()} disabled />);
    expect(screen.queryByLabelText("移除 adventure")).not.toBeInTheDocument();
  });
});
