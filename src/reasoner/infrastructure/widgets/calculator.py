"""
Calculator Widget

Evaluates mathematical expressions using simpleeval (safe evaluator).
"""

from __future__ import annotations

import re
import math
from typing import Any

from reasoner.infrastructure.widgets.protocol import BaseWidget, WidgetResult, WidgetType


class CalculatorWidget(BaseWidget):
    """
    Calculator widget for mathematical expressions.

    Features:
    - Basic arithmetic: +, -, *, /
    - Advanced: sin, cos, tan, log, sqrt, etc.
    - Constants: pi, e
    - Parentheses support
    """

    name = "calculator"
    widget_type = WidgetType.CALCULATOR
    description = "Mathematical expression evaluation"

    trigger_patterns = [
        # Pure math expressions
        re.compile(r'^[\d\+\-\*\/\.\(\)\s\^%]+$', re.I),
        # With math functions
        re.compile(r'^(?:calculate|compute|eval)\s*:?\s*(.+)$', re.I),
        # With "what is"
        re.compile(r"^what'?s?\s+(.+)$", re.I),
        # Percentage calculations
        re.compile(r'(\d+(?:\.\d+)?)\s*%\s*(?:of)?\s*(\d+(?:\.\d+)?)', re.I),
    ]

    def _extract_from_match(
        self,
        match: re.Match,
        query: str,
    ) -> dict[str, Any]:
        """Extract expression from match."""
        expression = None

        # Check for pure math expression
        if re.match(r'^[\d\+\-\*\/\.\(\)\s\^%]+$', query.strip()):
            expression = query.strip()
        else:
            # Get from capture group
            if match.lastindex and match.lastindex >= 1:
                expression = match.group(1).strip()

        # Clean up common phrases
        if expression:
            expression = re.sub(
                r"^(calculate|compute|eval|what'?s?)\s*:?\s*",
                '',
                expression,
                flags=re.I
            ).strip()

        return {'expression': expression or ''}

    async def _execute_impl(self, params: dict[str, Any]) -> dict[str, Any]:
        """Evaluate mathematical expression."""
        expression = params.get('expression', '')

        if not expression:
            return {'error': 'No expression provided'}

        # Try simpleeval first (safe expression evaluator)
        try:
            from simpleeval import simple_eval, EvalWithCompoundTypes
            
            # Create evaluator with math functions
            evaluator = EvalWithCompoundTypes()
            evaluator.names.update({
                'pi': math.pi,
                'e': math.e,
                'sqrt': math.sqrt,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'log': math.log,
                'log10': math.log10,
                'exp': math.exp,
                'abs': abs,
                'round': round,
                'floor': math.floor,
                'ceil': math.ceil,
            })
            
            result = evaluator.eval(expression)
            
            return {
                'expression': expression,
                'result': result,
                'result_formatted': self._format_result(result),
                'valid': True,
                'engine': 'simpleeval',
            }

        except ImportError:
            # Fallback to basic eval (limited)
            return self._basic_eval(expression)
        except Exception as e:
            return {
                'expression': expression,
                'error': str(e),
                'valid': False,
            }

    def _basic_eval(self, expression: str) -> dict[str, Any]:
        """Basic evaluation without simpleeval."""
        # Only allow safe characters
        allowed = set("0123456789+-*/.() ^%")
        if not all(c in allowed for c in expression):
            return {
                'expression': expression,
                'error': 'Invalid characters in expression',
                'valid': False,
            }

        try:
            # Safe eval with limited namespace
            result = eval(expression, {"__builtins__": {}}, {
                'pi': math.pi,
                'e': math.e,
            })

            return {
                'expression': expression,
                'result': result,
                'result_formatted': self._format_result(result),
                'valid': True,
                'engine': 'basic',
            }

        except Exception as e:
            return {
                'expression': expression,
                'error': str(e),
                'valid': False,
            }

    def _format_result(self, result: Any) -> str:
        """Format result for display."""
        if isinstance(result, float):
            # Round to reasonable precision
            if result == int(result):
                return str(int(result))
            return f"{result:.6g}"
        elif isinstance(result, complex):
            return f"{result.real:.6g} + {result.imag:.6g}i"
        else:
            return str(result)