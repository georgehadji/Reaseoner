'use client';

import { esc } from '@/lib/utils';

export function CalculationWidget({ expression, result }: { expression: string; result: number }) {
  return (
    <div className="widget calculation-widget">
      <div className="widget-header">
        <span className="widget-icon">🧮</span>
        <span className="widget-title">Calculation Result</span>
      </div>
      <div className="widget-content">
        <div className="calc-expression">{esc(expression)}</div>
        <div className="calc-result">= {result}</div>
      </div>
    </div>
  );
}
