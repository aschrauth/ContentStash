import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

export function formatDate(date: string | Date) {
  const dateObj = new Date(date);
  
  // Use toLocaleString to automatically convert to user's browser timezone
  return dateObj.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}


/**
 * Clean and normalize markdown text for proper rendering
 * Fixes common formatting issues from AI-generated content
 */
export function cleanMarkdown(text: string): string {
  if (!text) return '';
  
  let cleaned = text;
  
  // Fix bold colon spacing: Insert space after bold-colon if missing
  cleaned = cleaned.replace(/\*\*([^*]+):\*\*([^\s])/g, '**$1:** $2');
  
  // Fix escaped asterisks if present
  cleaned = cleaned.replace(/\\\*\\\*/g, '**');
  
  // Ensure blank line before lists (both ordered and unordered)
  // This regex looks for a non-list line followed immediately by a list item
  cleaned = cleaned.replace(/([^\n])\n((?:[-*+]|\d+\.)\s)/g, '$1\n\n$2');
  
  // Ensure blank line after lists end
  // This regex looks for a list item followed by a non-list, non-blank line
  cleaned = cleaned.replace(/((?:[-*+]|\d+\.)\s[^\n]+)\n([^\n](?![-*+]|\d+\.))/g, '$1\n\n$2');
  
  return cleaned;
}
