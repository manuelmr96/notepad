import { z } from "zod";

/**
 * Auth form schemas (D-12 inline validation).
 *
 * Messages are the exact UI-SPEC Copywriting Contract field-error strings so the
 * inline (Zod/RHF) errors match the design contract verbatim:
 *   - "Enter a valid email address."
 *   - "Password must be at least 8 characters."
 *
 * Password min length is 8 (UI-SPEC password policy, Claude's discretion within
 * CONTEXT.md). Login and register share the same client-side shape.
 */
export const loginSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

export const registerSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
