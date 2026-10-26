"""
Required demonstrations and pipeline regressions: DEM-01–02, ACC-06–12

Run from assigns/06:
python3 -m unittest discover -s MySolution -p 'test_*.py' -v
"""

import unittest
from copy import deepcopy
from unittest.mock import patch

import lambda1_vp as source
from compiler import compile_expr
from demo import runExample
from evaluator import evaluate
from examples import Example, requiredExamples
from observers import observe
from scope import freeVariables
from target import validateTarget


class TestRequiredExamples(unittest.TestCase):
    def test_catalog_has_all_fourteen_explicit_expectations(self):
        examples = requiredExamples()
        self.assertEqual([e.identifier for e in examples],
                         [f'DEMO-{n:02}' for n in range(1, 15)])
        self.assertEqual([e.expected for e in examples],
                         [14, 0, 7, 7, 2, True, 4, 1, 'step-budget exhaustion',
                          24, 5, 'step-budget exhaustion', False, True])
        self.assertEqual([e.identifier for e in examples if e.expectsExhaustion],
                         ['DEMO-09', 'DEMO-12'])

    def test_all_required_demonstrations_end_to_end(self):
        for example in requiredExamples():
            with self.subTest(example=example.identifier):
                snapshot = deepcopy(example.expression)
                term = compile_expr(example.expression)
                self.assertIsNone(validateTarget(term))
                self.assertEqual(freeVariables(term), set())
                result = runExample(example)
                self.assertTrue(result['passed'], result)
                self.assertEqual(example.expression, snapshot)
                execution = result['execution']
                self.assertLessEqual(execution['steps'], execution['budget'])
                if example.expectsExhaustion:
                    self.assertEqual(execution['status'], 'exhausted')
                    self.assertEqual(execution['steps'], execution['budget'])
                    self.assertIsNone(result['observation'])
                    self.assertIsNone(result['source_answer'])
                else:
                    self.assertEqual(execution['status'], 'completed')
                    self.assertEqual(result['source_answer'], example.expected)
                    observation = result['observation']
                    self.assertEqual(observation['status'], 'completed')
                    self.assertIs(type(observation['value']), type(example.expected))
                    self.assertEqual(observation['value'], example.expected)
                    self.assertLessEqual(observation['steps'], result['observation_budget'])

    def test_known_exhaustion_never_runs_source_evaluator(self):
        import demo
        realEvaluate = evaluate

        def guarded(term, *args, **kwargs):
            self.assertNotIsInstance(term, source.D0E000)
            return realEvaluate(term, *args, **kwargs)

        with patch.object(demo, 'evaluate', side_effect=guarded):
            for example in requiredExamples():
                if example.expectsExhaustion:
                    self.assertTrue(runExample(example)['passed'])

    def test_fresh_catalog_does_not_share_mutable_source_trees(self):
        first, second = requiredExamples(), requiredExamples()
        self.assertEqual(first, second)
        first[0].expression.arg1.arg1 = 999
        self.assertEqual(second[0].expression.arg1.arg1, 2)

    def test_exact_required_nested_pair(self):
        expression = source.D0Epair(source.D0Epair(
            source.D0Eint(2), source.D0Ebtf(True)), source.D0Eint(3))
        example = Example('nested', 'nested pair', expression,
                          ('pair', ('pair', 'nat', 'bool'), 'nat'), ((2, True), 3))
        result = runExample(example)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['observation']['value'], ((2, True), 3))

    def test_both_fix_binders_preserve_free_names(self):
        for name in ['f', 'x', 's', 'z', '_thunk_0']:
            expression = source.D0Efix('f', 'x', source.D0Epair(
                source.D0Evar('f'), source.D0Epair(
                    source.D0Evar('x'), source.D0Evar(name))))
            with self.subTest(name=name):
                self.assertEqual(freeVariables(compile_expr(expression)),
                                 set(source.d0exp_fvset(expression)))

    def test_nested_function_shadowing_of_each_fix_binder(self):
        for name in ['f', 'x']:
            expression = source.D0Eapp(source.D0Efix('f', 'x', source.D0Eapp(
                source.D0Elam(name, source.D0Evar(name)), source.D0Eint(7))),
                source.D0Eint(3))
            with self.subTest(name=name):
                self.assertEqual(evaluate(expression).arg1, 7)
                execution = evaluate(compile_expr(expression), 1000)
                self.assertEqual(execution.status, 'completed')
                observation = observe(execution.term, 'nat', 1000)
                self.assertEqual((observation.status, observation.value), ('completed', 7))


if __name__ == '__main__':
    unittest.main()
