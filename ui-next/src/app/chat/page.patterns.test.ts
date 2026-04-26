import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

const PAGE_PATH = path.resolve(__dirname, 'page.tsx');
const src = fs.readFileSync(PAGE_PATH, 'utf-8');

describe('chat/page.tsx patterns (BUG-002 & BUG-005 regression)', () => {
  it('does not mutate phases arrays via .push()', () => {
    // Before fix, phases.push(renderedPhase) and resumePhases.push(renderedPhase) existed
    const pushMatches = src.match(/phases\.push\(/g) || [];
    const resumePushMatches = src.match(/resumePhases\.push\(/g) || [];

    expect(pushMatches).toHaveLength(0);
    expect(resumePushMatches).toHaveLength(0);
  });

  it('uses immutable spread for phase accumulation', () => {
    // After fix: phases = [...phases, renderedPhase];
    expect(src).toContain('phases = [...phases, renderedPhase]');
    expect(src).toContain('resumePhases = [...resumePhases, renderedPhase]');
  });

  it('declares phases as let (reassignable) instead of const', () => {
    // After fix: let phases: RenderedPhase[] = [];
    expect(src).toContain('let phases: RenderedPhase[] = []');
    expect(src).toContain('let resumePhases: RenderedPhase[] = []');
  });

  it('includes RAF cleanup useEffect on unmount (BUG-005)', () => {
    // After fix: useEffect(() => { return () => { if (chunkFlushRafRef.current !== null) { cancelAnimationFrame(...) } } }, [])
    expect(src).toContain('cancelAnimationFrame(chunkFlushRafRef.current)');
    expect(src).toContain("useEffect(() => {\n    return () => {\n      if (chunkFlushRafRef.current !== null) {\n        cancelAnimationFrame(chunkFlushRafRef.current);\n        chunkFlushRafRef.current = null;\n      }\n    };\n  }, []);");
  });
});
