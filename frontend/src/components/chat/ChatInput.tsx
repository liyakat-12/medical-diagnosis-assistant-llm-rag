import { useState, type FormEvent, type KeyboardEvent } from "react";
import { Send, Square } from "lucide-react";
import { Textarea } from "../common/Textarea";
import { Button } from "../common/Button";

const STARTERS = [
  "I have a runny nose and sore throat for two days",
  "Burning when I pee and I need to go often",
  "Sudden crushing chest pain and shortness of breath",
  "Throbbing headache on one side with nausea and light sensitivity",
];

export function ChatInput({
  disabled,
  streaming,
  onSend,
  onStop,
}: {
  disabled?: boolean;
  streaming?: boolean;
  onSend: (value: string) => void;
  onStop: () => void;
}) {
  const [value, setValue] = useState("");

  function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue("");
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={submit} className="border-t border-teal-100/80 bg-white/90 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur">
      <div className="mx-auto max-w-3xl">
        <div className="mb-2 flex gap-2 overflow-x-auto pb-1">
          {STARTERS.map((item) => (
            <button
              key={item}
              type="button"
              className="shrink-0 rounded-full border border-teal-100 bg-teal-50 px-3 py-1.5 text-xs font-bold text-teal-900 hover:bg-teal-100"
              onClick={() => setValue(item)}
            >
              {item.slice(0, 32)}...
            </button>
          ))}
        </div>
        <div className="flex items-end gap-2 rounded-[1.6rem] border border-teal-100 bg-white p-2 shadow-sm">
          <Textarea
            label="Describe your symptoms"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            placeholder="Describe your symptoms in your own words..."
            disabled={disabled && !streaming}
            className="border-0 bg-transparent px-3 py-2 shadow-none focus:border-0 focus:ring-0"
          />
          {streaming ? (
            <Button type="button" variant="danger" className="mb-1 h-11 w-11 shrink-0 rounded-full px-0" onClick={onStop} aria-label="Stop generating">
              <Square size={16} />
            </Button>
          ) : (
            <Button type="submit" className="mb-1 h-11 w-11 shrink-0 rounded-full px-0" disabled={disabled || !value.trim()} aria-label="Send message">
              <Send size={16} />
            </Button>
          )}
        </div>
      </div>
    </form>
  );
}
