"""Predicate evaluator for rule matching"""

import re
from typing import Any, Dict, List, Optional, Union
from .context import RequestContext


class RuleEvaluator:
    """Pure predicate evaluator - no side effects, no database access"""

    @staticmethod
    def evaluate(predicate: Dict[str, Any], context: RequestContext) -> bool:
        """
        Evaluate a predicate tree against request context.

        Supports:
        - 'all': list of predicates (AND logic)
        - 'any': list of predicates (OR logic)
        - 'field'/'op'/'value': single condition
        """
        return evaluate_predicate(predicate, context)


def evaluate_predicate(predicate: Dict[str, Any], context: RequestContext) -> bool:
    """
    Recursively evaluate a predicate tree.

    Returns True if the predicate matches the context.
    """
    # Handle 'all' (AND)
    if 'all' in predicate:
        return all(
            evaluate_predicate(sub, context)
            for sub in predicate['all']
        )

    # Handle 'any' (OR)
    if 'any' in predicate:
        return any(
            evaluate_predicate(sub, context)
            for sub in predicate['any']
        )

    # Handle single condition
    if 'field' in predicate and 'op' in predicate:
        field = predicate['field']
        op = predicate['op']
        value = predicate.get('value')

        # Get field value from context
        field_value = context.get_field(field)

        # Evaluate the operator
        return evaluate_operator(field_value, op, value)

    # No valid predicate structure
    return False


def evaluate_operator(field_value: Any, op: str, compare_value: Any) -> bool:
    """
    Evaluate a single operator condition.

    Supported operators:
    - '=': equality
    - '!=': inequality
    - 'in': field_value in list
    - 'not_in': field_value not in list
    - 'contains': field_value contains item (for lists/strings)
    - '>': greater than
    - '>=': greater than or equal
    - '<': less than
    - '<=': less than or equal
    - 'between': field_value between two values
    - 'regex': field_value matches regex
    - 'exists': field_value is not None
    """
    if field_value is None:
        # None only matches 'exists' operator (when false) or != comparisons
        if op == 'exists':
            return False
        if op == '!=':
            return compare_value is None
        if op == 'not_in':
            return True
        return False

    if op == '=':
        return field_value == compare_value
    elif op == '!=':
        return field_value != compare_value
    elif op == 'in':
        return field_value in compare_value
    elif op == 'not_in':
        return field_value not in compare_value
    elif op == 'contains':
        if isinstance(field_value, (list, tuple)):
            return compare_value in field_value
        elif isinstance(field_value, str):
            return compare_value in field_value
        else:
            return False
    elif op == '>':
        try:
            return field_value > compare_value
        except TypeError:
            return False
    elif op == '>=':
        try:
            return field_value >= compare_value
        except TypeError:
            return False
    elif op == '<':
        try:
            return field_value < compare_value
        except TypeError:
            return False
    elif op == '<=':
        try:
            return field_value <= compare_value
        except TypeError:
            return False
    elif op == 'between':
        if isinstance(compare_value, (list, tuple)) and len(compare_value) == 2:
            try:
                return compare_value[0] <= field_value <= compare_value[1]
            except TypeError:
                return False
        return False
    elif op == 'regex':
        try:
            if isinstance(field_value, str):
                return bool(re.search(compare_value, field_value))
            else:
                return False
        except (re.error, TypeError):
            return False
    elif op == 'exists':
        return field_value is not None
    else:
        # Unknown operator
        return False
