"""
Real CLI and separate pipeline outcomes: DEM-01–02, QLT-04

Run from assigns/06:
python3 -m unittest discover -s MySolution -p 'test_*.py' -v
"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import demo
from examples import requiredExamples
from target import pretty
from compiler import compile_expr


class TestDemoCLI(unittest.TestCase):
    def runCLI(self, *arguments, cwd=None):
        return subprocess.run(
            [sys.executable, str(Path(demo.__file__).resolve()), *arguments],
            cwd=cwd, capture_output=True, text=True, timeout=30)

    def test_default_command_runs_all_and_saves_full_pure_terms(self):
        with tempfile.TemporaryDirectory() as directory:
            process = self.runCLI(cwd=directory)
            self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
            self.assertIn('14/14 demonstrations passed.', process.stdout)
            self.assertIn('does not prove nontermination', process.stdout)
            self.assertIn('Observation: skipped', process.stdout)
            self.assertIn('Decoded answer: 24', process.stdout)
            for example in requiredExamples():
                path = Path(directory, 'demo_terms', example.identifier + '.lambda.txt')
                self.assertEqual(path.read_text(), pretty(compile_expr(example.expression)) + '\n')
                self.assertIn(str(path), process.stdout)

    def test_json_selection_and_separate_counts(self):
        process = self.runCLI('--example', 'DEMO-01', '--inline-terms', '--json')
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        self.assertEqual((report['passed'], report['total']), (1, 1))
        result = report['results'][0]
        self.assertEqual(result['source_answer'], 14)
        self.assertEqual(result['observation']['value'], 14)
        self.assertGreater(result['execution']['steps'], 0)
        self.assertGreater(result['observation']['steps'], 0)
        self.assertEqual(result['execution']['budget'], 10000)
        self.assertEqual(result['observation_budget'], 10000)
        self.assertIsNone(result['generated_term_file'])
        self.assertEqual(result['generated_term'], pretty(compile_expr(requiredExamples()[0].expression)))

    def test_execution_exhaustion_is_a_failed_terminating_example(self):
        process = self.runCLI('--example', 'DEMO-01', '--execution-budget', '0',
                              '--inline-terms', '--json')
        self.assertEqual(process.returncode, 1)
        result = json.loads(process.stdout)['results'][0]
        self.assertEqual(result['execution'], {'status': 'exhausted', 'steps': 0, 'budget': 0})
        self.assertIsNone(result['observation'])
        self.assertFalse(result['passed'])

    def test_observation_exhaustion_is_separate_from_execution(self):
        process = self.runCLI('--example', 'DEMO-01', '--observation-budget', '0',
                              '--inline-terms', '--json')
        self.assertEqual(process.returncode, 1)
        result = json.loads(process.stdout)['results'][0]
        self.assertEqual(result['execution']['status'], 'completed')
        self.assertEqual(result['observation']['status'], 'exhausted')
        self.assertEqual(result['observation']['steps'], 0)
        self.assertIsNone(result['observation']['value'])

    def test_invalid_cli_inputs_are_rejected(self):
        for arguments in [('--execution-budget', '-1'), ('--observation-budget', '1.5'),
                          ('--example', 'missing')]:
            with self.subTest(arguments=arguments):
                process = self.runCLI(*arguments)
                self.assertEqual(process.returncode, 2)
                self.assertIn('error:', process.stderr)

    def test_mismatch_is_reported_and_returns_failure(self):
        from dataclasses import replace
        example = replace(requiredExamples()[0], expected=99)
        result = demo.runExample(example)
        self.assertFalse(result['passed'])
        self.assertEqual(result['source_answer'], 14)
        self.assertEqual(result['observation']['value'], 14)

    def test_malformed_observation_is_preserved_as_failure(self):
        from observers import ObservationResult
        with patch.object(demo, 'observe', return_value=ObservationResult(
                'malformed', None, 2, 'bad data shape')):
            result = demo.runExample(requiredExamples()[0])
        self.assertFalse(result['passed'])
        self.assertEqual(result['observation']['status'], 'malformed')
        self.assertEqual(result['observation']['message'], 'bad data shape')

    def test_example_error_does_not_hide_remaining_results(self):
        import contextlib
        import io
        results = [RuntimeError('example failed'),
                   {'id': 'DEMO-02', 'passed': True}]
        output = io.StringIO()
        with patch.object(demo, 'runExample', side_effect=results), \
                contextlib.redirect_stdout(output):
            status = demo.main(['--example', 'DEMO-01', '--example', 'DEMO-02', '--json'])
        self.assertEqual(status, 1)
        report = json.loads(output.getvalue())
        self.assertEqual((report['passed'], report['total']), (1, 2))
        self.assertIn('RuntimeError', report['results'][0]['error'])


if __name__ == '__main__':
    unittest.main()
