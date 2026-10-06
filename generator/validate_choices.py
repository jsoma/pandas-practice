"""Build conceptual distractors; runtime errors are allowed, arbitrary typos are not."""
from pathlib import Path
import ast
import copy
import json
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grading import evaluate, equivalent
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = {'value_counts': ['count', 'unique', 'nunique', 'sum'],
              'mean': ['sum', 'count', 'median', 'max', 'value_counts', 'unique'],
              'sum': ['mean', 'count', 'nunique', 'min', 'value_counts', 'unique'],
              'size': ['count', 'nunique', 'sum'],
              'count': ['sum', 'mean', 'nunique'],
              'nunique': ['count', 'unique', 'value_counts'],
              'groupby': ['sort_values'], 'sort_values': ['sort_index', 'min', 'max'],
              'head': ['tail'], 'tail': ['head'], 'isin': ['value_counts', 'unique']}


def order_matters(question):
    # The prompt sets the contract, not an incidental sort in the sample solution.
    return bool(re.search(r'\b(highest|lowest|top|bottom|most common|least common|sorted|ordered|ascending|descending|first|last)\b', question, re.I))


def candidates(code):
    tree = ast.parse(code, mode='eval')
    nodes = list(ast.walk(tree))
    # Reverse chained pandas operations, keeping complete valid Python syntax.
    for index, node in enumerate(nodes):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Call)
                and isinstance(node.func.value.func, ast.Attribute)):
            changed = copy.deepcopy(tree)
            outer = list(ast.walk(changed))[index]
            inner = outer.func.value
            outer.func.attr, inner.func.attr = inner.func.attr, outer.func.attr
            outer.args, inner.args = inner.args, outer.args
            outer.keywords, inner.keywords = inner.keywords, outer.keywords
            yield ast.unparse(changed)
    # Default ascending sorting can be confused with descending sorting.
    for index, node in enumerate(nodes):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'sort_values'
                and not any(k.arg == 'ascending' for k in node.keywords)):
            changed = copy.deepcopy(tree)
            list(ast.walk(changed))[index].keywords.append(ast.keyword(arg='ascending', value=ast.Constant(False)))
            yield ast.unparse(changed)
    # Select a different pandas operation while retaining the same column and inputs.
    for index, node in enumerate(nodes):
        if isinstance(node, ast.Attribute):
            for replacement in OPERATIONS.get(node.attr, []):
                changed = copy.deepcopy(tree)
                list(ast.walk(changed))[index].attr = replacement
                yield ast.unparse(changed)
        elif isinstance(node, ast.Compare):
            for operator in [ast.NotEq, ast.Eq, ast.Gt, ast.Lt, ast.GtE, ast.LtE]:
                changed = copy.deepcopy(tree)
                target = list(ast.walk(changed))[index]
                target.ops = [operator() for _ in target.ops]
                yield ast.unparse(changed)
        elif isinstance(node, ast.keyword) and node.arg in ['ascending', 'normalize'] and isinstance(node.value, ast.Constant):
            changed = copy.deepcopy(tree)
            list(ast.walk(changed))[index].value.value = not node.value.value
            yield ast.unparse(changed)
    # A boolean mask identifies matches, but does not select the requested rows.
    if isinstance(tree.body, ast.Subscript) and isinstance(tree.body.slice, ast.Compare):
        yield ast.unparse(tree.body.slice)
        column = tree.body.slice.left
        for operation in ['value_counts', 'count', 'unique']:
            yield ast.unparse(column) + '.' + operation + '()'


def build(bank):
    frames = {}
    for q in bank['questions']:
        if q['dataset'] not in frames:
            frames[q['dataset']] = pd.read_csv(ROOT / 'datasets' / q['dataset'])
        df = frames[q['dataset']]
        code = q['canonicalAnswer']['code']
        expected = evaluate(code, df)
        q['answerOrderMatters'] = order_matters(q['question'])
        choices = []
        for candidate in dict.fromkeys(candidates(code)):
            if candidate == code: continue
            try:
                result = evaluate(candidate, df)
                if equivalent(expected, result, preserve_order=q['answerOrderMatters']): continue
            except SyntaxError:
                # Never use malformed syntax or unsupported constructs as distractors.
                continue
            except (AttributeError, TypeError, KeyError, ValueError):
                # Wrong pandas operations/order may fail at runtime: that is intentional.
                pass
            choices.append(candidate)
            if len(choices) == 3: break
        if len(choices) != 3: raise ValueError('Not enough conceptual distractors for ' + q['id'])
        q['distractors'] = choices
    return bank

if __name__ == '__main__':
    path = ROOT / 'questions.json'
    path.write_text(json.dumps(build(json.loads(path.read_text())), indent=2) + '\n')
