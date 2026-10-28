const SEP_CELL = /^:?-{3,}:?$/;

function cells(row: string): string[] {
  return row.trim().replace(/^\||\|$/g, "").split("|").map((part) => part.trim());
}

function isSeparator(row: string): boolean {
  const parts = cells(row).map((cell) => cell.replace(/\s/g, ""));
  return parts.length > 0 && parts.every((cell) => SEP_CELL.test(cell));
}

function separatorRow(count: number): string {
  return `| ${Array.from({ length: Math.max(count, 1) }, () => "---").join(" | ")} |`;
}

function rowToBullet(row: string): string {
  const parts = cells(row).filter((cell) => cell && !SEP_CELL.test(cell.replace(/\s/g, "")));
  if (parts.length >= 2) return `- **${parts[0]}**: ${parts.slice(1).join(" — ")}`;
  if (parts[0]) return `- ${parts[0]}`;
  return "";
}

function splitConcatenatedRows(line: string): string[] {
  const text = line.trim();
  if ((text.match(/\|/g) || []).length < 4) return text.includes("|") ? [text] : [];
  const parts = text.split(/(?<=\|)\s+(?=\|)/).map((part) => part.trim()).filter(Boolean);
  return parts.length >= 2 ? parts : [text];
}

function formatTable(rows: string[]): string {
  const cleaned = rows.map((row) => row.trim()).filter(Boolean);
  if (!cleaned.length) return "";
  const columns = cells(cleaned[0]).length;
  if (columns < 2 || cleaned.length === 1) {
    return cleaned.map(rowToBullet).filter(Boolean).join("\n");
  }
  const header = cleaned[0];
  let body = cleaned.slice(1);
  const formatted = [header];
  if (body[0] && isSeparator(body[0])) {
    formatted.push(separatorRow(columns));
    body = body.slice(1);
  } else {
    formatted.push(separatorRow(columns));
  }
  if (!body.length) return cleaned.map(rowToBullet).filter(Boolean).join("\n");
  return [...formatted, ...body].join("\n");
}

export function normalizeMarkdownTables(text: string): string {
  if (!text || !text.includes("|")) return text || "";
  let cleaned = text.replace(/\r\n/g, "\n");
  if (cleaned.includes("\\n") && (cleaned.match(/\n/g) || []).length < 2) {
    cleaned = cleaned.replace(/\\n/g, "\n");
  }
  const lines = cleaned.split("\n");
  const rebuilt: string[] = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.includes("|")) {
      rebuilt.push(line);
      index += 1;
      continue;
    }
    let tableLine = line;
    const pipeAt = line.indexOf("|");
    if (pipeAt > 0) {
      const prefix = line.slice(0, pipeAt).trimEnd();
      if (prefix) rebuilt.push(prefix);
      tableLine = line.slice(pipeAt);
    }
    const rows = splitConcatenatedRows(tableLine);
    index += 1;
    while (index < lines.length && lines[index].includes("|")) {
      rows.push(...splitConcatenatedRows(lines[index]));
      index += 1;
    }
    if (rebuilt.length && rebuilt[rebuilt.length - 1].trim()) rebuilt.push("");
    rebuilt.push(formatTable(rows));
  }
  return rebuilt.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

export function looksLikeGfmTable(text: string): boolean {
  return /\|.+\|\n\|\s*:?-{3,}/.test(normalizeMarkdownTables(text));
}
