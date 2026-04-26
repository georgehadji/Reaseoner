import { describe, expect, it } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

describe('globals.css', () => {
  const cssPath = path.join(__dirname, 'globals.css');
  const css = fs.readFileSync(cssPath, 'utf-8');

  it('uses Tailwind v4 @import syntax instead of deprecated @tailwind directives', () => {
    expect(css).toContain('@import "tailwindcss"');
    expect(css).not.toContain('@tailwind base');
    expect(css).not.toContain('@tailwind components');
    expect(css).not.toContain('@tailwind utilities');
  });

  it('retains custom @layer base and @layer utilities blocks', () => {
    expect(css).toContain('@layer base {');
    expect(css).toContain('@layer utilities {');
  });
});
