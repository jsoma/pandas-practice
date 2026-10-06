"""Result-based grading shared by the browser worker and regression checks."""
import ast
import io
import json
import numpy as np
import pandas as pd

METHODS = {'value_counts', 'groupby', 'size', 'count', 'unique', 'nunique',
           'sum', 'mean', 'min', 'max', 'median', 'head', 'tail', 'sort_values',
           'sort_index', 'nlargest', 'nsmallest', 'isin', 'query', 'reset_index',
           'dropna', 'fillna', 'round', 'agg', 'rename', 'to_frame'}
# Expressions and optional assignments only; no imports, loops, or access to Python internals.
NODES = (ast.Module, ast.Expr, ast.Assign, ast.Name, ast.Load, ast.Store,
         ast.Constant, ast.Subscript, ast.Slice, ast.List, ast.Tuple, ast.Dict,
         ast.Call, ast.Attribute, ast.keyword, ast.Compare, ast.Eq, ast.NotEq,
         ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.BinOp, ast.Add, ast.Sub,
         ast.Mult, ast.Div, ast.BitAnd, ast.BitOr, ast.UnaryOp, ast.Invert,
         ast.USub, ast.UAdd)


def evaluate(code, df):
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if not isinstance(node, NODES):
            raise ValueError('Use pandas expressions or assignments, ending with your result.')
        if isinstance(node, ast.Name) and node.id.startswith('_'):
            raise ValueError('Private names are not supported.')
        if isinstance(node, ast.Attribute) and node.attr not in METHODS:
            raise ValueError('Unsupported pandas method: ' + node.attr)
        if isinstance(node, ast.Call) and not (
            isinstance(node.func, ast.Attribute) or
            isinstance(node.func, ast.Name) and node.func.id == 'len'
        ):
            raise ValueError('Only pandas methods and len() are supported.')
        if isinstance(node, ast.Assign) and any(not isinstance(t, ast.Name) for t in node.targets):
            raise ValueError('Assign results to a variable instead of modifying the dataset.')
    if not tree.body:
        raise ValueError('Enter an answer.')
    env = {'df': df.copy(deep=True), 'len': len, '__builtins__': {}}
    for statement in tree.body[:-1]:
        exec(compile(ast.Module(body=[statement], type_ignores=[]), '<answer>', 'exec'), env)
    last = tree.body[-1]
    if isinstance(last, ast.Assign):
        exec(compile(ast.Module(body=[last], type_ignores=[]), '<answer>', 'exec'), env)
        return env[last.targets[0].id]
    return eval(compile(ast.Expression(last.value), '<answer>', 'eval'), env)


def equivalent(expected, actual, preserve_order=True):
    try:
        if isinstance(expected, pd.DataFrame) and isinstance(actual, pd.DataFrame):
            pd.testing.assert_frame_equal(expected, actual, check_dtype=False, check_names=False, check_like=not preserve_order)
        elif isinstance(expected, pd.Series) and isinstance(actual, pd.Series):
            if not preserve_order:
                if not expected.index.is_unique or not actual.index.is_unique:
                    return False
                if len(expected) != len(actual) or len(expected.index.difference(actual.index)):
                    return False
                actual = actual.reindex(expected.index)
            pd.testing.assert_series_equal(expected, actual, check_dtype=False, check_names=False)
        elif np.isscalar(expected) and np.isscalar(actual):
            if isinstance(expected, (int, float, np.number)) and isinstance(actual, (int, float, np.number)):
                return bool(np.isclose(expected, actual, rtol=1e-7, atol=1e-9, equal_nan=True))
            return bool(expected == actual)
        else:
            return False
        return True
    except (AssertionError, TypeError, ValueError):
        return False


def grade(csv, canonical, answer, preserve_order=True):
    df = pd.read_csv(io.StringIO(csv))
    expected = evaluate(canonical, df)
    try:
        actual = evaluate(answer, df)
        correct = equivalent(expected, actual, preserve_order=preserve_order)
        return json.dumps({'correct': correct, 'message': 'Correct!' if correct else 'The result differs from the expected answer. Try again.'})
    except Exception as error:
        return json.dumps({'correct': False, 'message': str(error)})
