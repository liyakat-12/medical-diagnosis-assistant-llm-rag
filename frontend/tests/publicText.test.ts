import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join } from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import { publicError, publicStatus } from "../src/utils/publicText.ts";

const FRONTEND_SRC = join(dirname(fileURLToPath(import.meta.url)), "../src");
const FORBIDDEN = [
  "groq",
  "openai",
  "ollama",
  "chatgpt",
  "gpt-oss",
  "gsk_",
  "vite_groq",
  "vite_openai",
  "groq_api_key",
  "openai_api_key",
];

function walk(dir: string, files: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walk(full, files);
    else if ([".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".json"].includes(extname(full))) files.push(full);
  }
  return files;
}

describe("public copy", () => {
  it("keeps MediAssist status and error fallbacks", () => {
    assert.equal(publicStatus(""), "MediAssist is preparing a reply...");
    assert.match(publicError(""), /try again/i);
    assert.match(publicError("Groq 429"), /try again/i);
    assert.match(publicError("Unable to send your message. Please try again."), /try again/i);
  });

  it("does not ship vendor names or provider credentials in frontend source", () => {
    for (const file of walk(FRONTEND_SRC)) {
      const text = readFileSync(file, "utf8").toLowerCase();
      for (const marker of FORBIDDEN) {
        assert.equal(text.includes(marker), false, `${file} contains ${marker}`);
      }
    }
  });
});
