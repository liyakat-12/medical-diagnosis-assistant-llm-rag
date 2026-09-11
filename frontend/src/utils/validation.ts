export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}

export function passwordIssues(password: string): string[] {
  const issues: string[] = [];
  if (password.length < 8) issues.push("Use at least 8 characters.");
  if (!/[A-Za-z]/.test(password)) issues.push("Include a letter.");
  if (!/\d/.test(password)) issues.push("Include a number.");
  return issues;
}
