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
    <form onSubmit={submit} className="border-t border-teal-100 bg-white/95 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <div className="mb-2 flex gap-2 overflow-x-auto pb-1">
        {STARTERS.map((item) => (
          <button
            key={item}
            type="button"
            className="shrink-0 rounded-full border border-teal-100 bg-teal-50 px-3 py-1 text-xs font-bold text-teal-900"
            onClick={() => setValue(item)}
          >
            {item.slice(0, 28)}...
          </button>
        ))}
      </div>
      <div className="flex items-end gap-2">
        <Textarea
          label="Describe your symptoms"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={onKeyDown}
          rows={3}
          placeholder="Describe your symptoms in your own words..."
          disabled={disabled && !streaming}
        />
        {streaming ? (
          <Button type="button" variant="danger" onClick={onStop} aria-label="Stop generating">
            <Square size={16} />
          </Button>
        ) : (
          <Button type="submit" disabled={disabled || !value.trim()} aria-label="Send message">
            <Send size={16} />
          </Button>
        )}
      </div>
    </form>
  );
}
