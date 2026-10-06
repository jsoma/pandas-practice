import ast
import json
import sys
import unittest
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from grading import evaluate, equivalent, grade

class GradingTests(unittest.TestCase):
    def test_all_questions_and_distractors(self):
        bank = json.loads((ROOT / 'questions.json').read_text())['questions']
        frames = {}
        for q in bank:
            if q['dataset'] not in frames:
                frames[q['dataset']] = pd.read_csv(ROOT / 'datasets' / q['dataset'])
            df = frames[q['dataset']]
            expected = evaluate(q['canonicalAnswer']['code'], df)
            self.assertEqual(len(set(q['distractors'])), 3, q['id'])
            for distractor in q['distractors']:
                ast.parse(distractor, mode='eval')
                try:
                    actual = evaluate(distractor, df)
                except (AttributeError, TypeError, KeyError, ValueError):
                    continue
                self.assertFalse(equivalent(expected, actual, preserve_order=q['answerOrderMatters']), (q['id'], distractor))

    def test_real_equivalents(self):
        csv = 'category,value\na,1\nb,2\na,3\n'
        for answer in ['df["value"].mean()', 'answer = df["value"].sum() / len(df)\nanswer',
                       '# compute average\ndf["value"].mean()']:
            self.assertTrue(json.loads(grade(csv, "df['value'].mean()", answer))['correct'])

    def test_invalid_and_wrong_answers(self):
        csv = 'category,value\na,1\nb,2\na,3\n'
        canonical = "df['category'].value_counts()"
        for answer in ['garbage.value_counts()', "df['value'].value_counts()", "df['category'].value_counts().head(1)",
                       'import os', 'df.__class__', '__import__("os")', 'while True: pass']:
            self.assertFalse(json.loads(grade(csv, canonical, answer))['correct'], answer)

    def test_shape_and_order_matter(self):
        df = pd.DataFrame({'value': [1, 2]})
        self.assertFalse(equivalent(df, df.head(1)))
        self.assertFalse(equivalent(df, df.tail(2).sort_values('value', ascending=False)))
        self.assertFalse(equivalent(df['value'], 3))

    def test_unordered_group_counts_on_real_dataset(self):
        q = next(q for q in json.loads((ROOT / 'questions.json').read_text())['questions']
                 if q['id'] == 'wreckers_groupby_count_015')
        csv = (ROOT / 'datasets' / q['dataset']).read_text()
        self.assertFalse(q['answerOrderMatters'])
        self.assertTrue(json.loads(grade(csv, q['canonicalAnswer']['code'],
            "df.groupby('DBA Name').size()", preserve_order=False))['correct'])

    def test_unordered_alignment_keeps_labels_and_values(self):
        expected = pd.Series([2, 1], index=['a', 'b'])
        actual = pd.Series([1, 2], index=['b', 'a'])
        self.assertTrue(equivalent(expected, actual, preserve_order=False))
        self.assertFalse(equivalent(expected, actual, preserve_order=True))
        self.assertFalse(equivalent(expected, pd.Series([2, 1], index=['b', 'a']), preserve_order=False))
        self.assertFalse(equivalent(expected, pd.Series([2, 1], index=['a', 'c']), preserve_order=False))

    def test_conceptual_runtime_errors_are_generated(self):
        from generator.validate_choices import candidates
        examples = list(candidates("df['category'].value_counts().head(1)"))
        self.assertIn("df['category'].head(1).value_counts()", examples)
        self.assertIn("df['category'].count().head(1)", examples)
        for code in examples:
            ast.parse(code, mode='eval')
            self.assertNotIn('.size()', code)
        csv = 'category\na\nb\na\n'
        self.assertFalse(json.loads(grade(csv, "df['category'].value_counts().head(1)",
            "df['category'].count().head(1)"))['correct'])

if __name__ == '__main__':
    unittest.main()
