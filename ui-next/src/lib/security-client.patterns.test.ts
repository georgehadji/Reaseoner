import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const FILE_PATH = path.resolve(__dirname, 'security-client.ts');
const src = fs.readFileSync(FILE_PATH, 'utf-8');

describe('security-client patterns (BUG-012 regression)', () => {
  it('does not throw after initiating 401 redirect', () => {
    // Extract the block inside the 401 handler
    const blockMatch = src.match(/if \(resp\.status === 401\) \{([\s\S]*?)\n  \}/);
    expect(blockMatch).toBeTruthy();
    const block = blockMatch![1];

    // Must contain window.location.href assignment
    expect(block).toContain("window.location.href = '/login'");

    // Must NOT contain a throw statement
    expect(block).not.toContain('throw');

    // Must return a never-resolving promise instead
    expect(block).toContain('new Promise(() => {})');
  });
});
