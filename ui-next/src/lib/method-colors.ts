import { METHOD_ACCENT_HEX, METHOD_ACCENT_RGB, type MethodId } from './design-tokens';

/**
 * Re-exporting from design-tokens to maintain backward compatibility
 * while ensuring a single source of truth.
 */
export { METHOD_ACCENT_HEX, METHOD_ACCENT_RGB, type MethodId };

/** Default fallback when no method is active. */
export const DEFAULT_ACCENT_RGB: [number, number, number] = METHOD_ACCENT_RGB['multi-perspective'];
