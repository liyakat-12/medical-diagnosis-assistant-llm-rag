import { useState } from "react";
import { Button } from "../common/Button";
import { cn } from "../../lib/cn";

const DURATION = ["A few hours", "1-2 days", "About a week", "More than 2 weeks"];
const AGES = ["Under 18", "18-40", "41-60", "Over 60"];
const WORSE = ["Movement", "Rest", "Eating", "Breathing", "Light or sound", "Not sure"];

export interface FollowUpAnswers {
  duration: string;
  age: string;
  worse: string;
}

function ChoiceRow({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (next: string) => void;
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-extrabold text-slate-900">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            className={cn(
              "min-h-11 rounded-full border px-3 py-1.5 text-xs font-bold",
              value === option ? "border-teal-700 bg-teal-700 text-white" : "border-teal-100 bg-teal-50 text-teal-900 hover:bg-teal-100",
            )}
            onClick={() => onChange(option)}
          >
            {option}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export function FollowUpCard({
  symptoms,
  onContinue,
  onSkip,
}: {
  symptoms: string;
  onContinue: (answers: FollowUpAnswers) => void;
  onSkip: () => void;
}) {
  const [duration, setDuration] = useState("");
  const [age, setAge] = useState("");
  const [worse, setWorse] = useState("");
  const ready = Boolean(duration && age && worse);

  return (
    <article className="flex max-w-[min(48rem,100%)] gap-3">
      <div className="min-w-0 flex-1 rounded-3xl border border-teal-100 bg-white px-4 py-4 shadow-sm">
        <p className="text-sm font-extrabold text-slate-900">A few quick details first</p>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          Answer these three questions, then I will show four possible matches, urgency, and nearby hospitals.
        </p>
        <p className="mt-3 max-h-32 overflow-y-auto rounded-2xl bg-teal-50 px-3 py-2 text-sm leading-6 break-anywhere text-slate-700">“{symptoms}”</p>
        <div className="mt-4 space-y-4">
          <ChoiceRow label="1. How long has this been going on?" options={DURATION} value={duration} onChange={setDuration} />
          <ChoiceRow label="2. What is your age group?" options={AGES} value={age} onChange={setAge} />
          <ChoiceRow label="3. What makes it worse?" options={WORSE} value={worse} onChange={setWorse} />
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button disabled={!ready} onClick={() => onContinue({ duration, age, worse })}>
            Continue to results
          </Button>
          <Button variant="secondary" onClick={onSkip}>
            Skip questions
          </Button>
        </div>
      </div>
    </article>
  );
}

export function formatFollowUpQuery(symptoms: string, answers: FollowUpAnswers): string {
  return `${symptoms.trim()}\n\nExtra detail: lasting ${answers.duration}; age group ${answers.age}; worse with ${answers.worse}.`;
}
