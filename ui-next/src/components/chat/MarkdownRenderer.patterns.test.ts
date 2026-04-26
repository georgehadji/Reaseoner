import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const FILE_PATH = path.resolve(__dirname, 'MarkdownRenderer.tsx');
const src = fs.readFileSync(FILE_PATH, 'utf-8');

describe('MarkdownRenderer patterns (BUG-011 regression)', () => {
  it('does not use rest spread on anchor tag renderer', () => {
    // Find the anchor renderer function
    const anchorMatch = src.match(/a\(\{[^}]+\}\)/);
    expect(anchorMatch).toBeTruthy();
    const anchorSig = anchorMatch![0];

    // Must not contain ...rest
    expect(anchorSig).not.toContain('...rest');

    // Should use explicit props instead
    expect(anchorSig).toContain('title');
  });

  it('passes only known safe props to anchor element', () => {
    const anchorBlockMatch = src.match(
      /a\(\{[^}]+\}\)\s*\{[\s\S]*?return\s*\(\s*<a[\s\S]*?<\/a>\s*\);/,
    );
    expect(anchorBlockMatch).toBeTruthy();
    const anchorBlock = anchorBlockMatch![0];

    // Only href, target, rel, and title should appear on the <a> tag
    expect(anchorBlock).toContain('href={href}');
    expect(anchorBlock).toContain('target="_blank"');
    expect(anchorBlock).toContain('rel="noopener noreferrer"');
    expect(anchorBlock).toContain('title={title}');
    expect(anchorBlock).not.toMatch(/\{\.\.\./);
  });
});
