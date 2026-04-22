'use client';

import { CalculationWidget } from './CalculationWidget';
import { StockWidget } from './StockWidget';
import { WeatherWidget } from './WeatherWidget';

export interface WidgetData {
  widget_type: string;
  name: string;
  result: Record<string, unknown>;
  citations?: string[];
}

const WIDGET_MAP: Record<string, React.FC<any>> = {
  calculator: CalculationWidget,
  stock: StockWidget,
  weather: WeatherWidget,
};

export function WidgetRenderer({ widget }: { widget: WidgetData }) {
  const Component = WIDGET_MAP[widget.widget_type];
  if (!Component) {
    return (
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm text-[var(--text-muted)]">
        Unknown widget: {widget.widget_type}
      </div>
    );
  }

  // Adapt data shape to each widget's expected props
  if (widget.widget_type === 'calculator') {
    return (
      <Component
        expression={(widget.result.expression as string) || ''}
        result={(widget.result.result as number) || 0}
      />
    );
  }

  return <Component data={widget.result} />;
}
