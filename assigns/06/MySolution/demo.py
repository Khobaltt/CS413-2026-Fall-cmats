"""
Command-line compilation, execution, and observation: DEM-01, DEM-02

Run from assigns/06 (Python 3.12+):
python3 MySolution/demo.py

Generated pure terms are saved in demo_terms/ unless --inline-terms is used.
Execution and observation each receive their own beta-value step budget.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import lambda1_vp as source
from compiler import compile_expr
from evaluator import evaluate
from examples import Example, requiredExamples
from observers import observe
from target import pretty
from visitors import PrettyPrintVisitor


def sourceValue(value, kind):
    """Inspect source values only; encoded computation belongs to observers."""
    if kind == 'nat' and type(value) is source.D0Vint:
        return value.arg1
    if kind == 'bool' and type(value) is source.D0Vbtf:
        return value.arg1
    if type(kind) is tuple and type(value) is source.D0Vpair:
        return (sourceValue(value.arg1, kind[1]), sourceValue(value.arg2, kind[2]))
    raise TypeError(f'Source value does not match expected kind {kind!r}')


def sameValue(actual, expected):
    """Keep False distinct from 0 when checking decoded results."""
    if type(actual) is not type(expected):
        return False
    if type(expected) is tuple:
        return len(actual) == len(expected) and all(
            sameValue(a, e) for a, e in zip(actual, expected))
    return actual == expected


def runExample(example: Example, executionBudget=None, observationBudget=None,
               termsDirectory: Path | None = None) -> dict:
    """Run the real pipeline. None for termsDirectory returns an inline term.

    Never run the unbounded source evaluator for known exhaustion examples.
    Observation always receives the completed execution value, not the
    original program, so the execution cost is not counted twice.
    """
    executionBudget = (example.executionBudget if executionBudget is None
                       else executionBudget)
    observationBudget = (example.observationBudget if observationBudget is None
                         else observationBudget)
    for budget in (executionBudget, observationBudget):
        if type(budget) is not int or budget < 0:
            raise ValueError('Budgets must be nonnegative integers')
    term = compile_expr(example.expression)
    text = pretty(term)
    termPath = None
    if termsDirectory is not None:
        termsDirectory = Path(termsDirectory)
        termsDirectory.mkdir(parents=True, exist_ok=True)
        path = termsDirectory / f'{example.identifier}.lambda.txt'
        path.write_text(text + '\n', encoding='utf-8')
        termPath = str(path.resolve())

    sourceAnswer = None
    if not example.expectsExhaustion:
        sourceAnswer = sourceValue(evaluate(example.expression), example.kind)
    execution = evaluate(term, executionBudget)
    observation = None
    if execution.status == 'completed' and not example.expectsExhaustion:
        observation = observe(execution.term, example.kind, observationBudget)

    if example.expectsExhaustion:
        passed = execution.status == 'exhausted'
    else:
        passed = (sameValue(sourceAnswer, example.expected)
                  and execution.status == 'completed'
                  and observation is not None
                  and observation.status == 'completed'
                  and sameValue(observation.value, example.expected))
    return {
        'id': example.identifier,
        'title': example.title,
        'source': example.expression.accept(PrettyPrintVisitor()),
        'expected_kind': example.kind,
        'expected': example.expected,
        'source_status': 'skipped (unbounded source evaluator)' if
                         example.expectsExhaustion else 'completed',
        'source_answer': sourceAnswer,
        'generated_term_file': termPath,
        'generated_term': text if termPath is None else None,
        'execution': {'budget': executionBudget, 'status': execution.status,
                      'steps': execution.steps},
        'observation_budget': observationBudget,
        'observation': asdict(observation) if observation is not None else None,
        'passed': passed,
    }


def displayValue(value):
    if type(value) is bool:
        return 'true' if value else 'false'
    if type(value) is tuple:
        return '(' + ', '.join(displayValue(part) for part in value) + ')'
    return str(value)


def printResult(result):
    print(f"\n{result['id']}: {result['title']}")
    print(f"  Source: {result['source']}")
    print('  Generated pure term: ' + (result['generated_term_file'] or
                                        result['generated_term']))
    print(f"  Expected ({result['expected_kind']}): {displayValue(result['expected'])}")
    print(f"  Source evaluation: {result['source_status']}", end='')
    if result['source_status'] == 'completed':
        print(f"; answer={displayValue(result['source_answer'])}")
    else:
        print()
    execution = result['execution']
    print(f"  Execution: {execution['status']}; beta-value steps="
          f"{execution['steps']}; budget={execution['budget']}")
    observation = result['observation']
    if observation is None:
        print(f"  Observation: skipped; steps=0; budget={result['observation_budget']}")
        print('  Decoded answer: unavailable')
    else:
        print(f"  Observation: {observation['status']}; beta-value steps="
              f"{observation['steps']}; budget={result['observation_budget']}")
        print('  Decoded answer: ' + (displayValue(observation['value'])
              if observation['status'] == 'completed' else 'unavailable'))
        if observation['message']:
            print(f"  Observation detail: {observation['message']}")
    print('  Check: ' + ('PASS' if result['passed'] else 'FAIL'))


def nonnegative(text):
    try:
        value = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError('Use a nonnegative integer') from error
    if value < 0:
        raise argparse.ArgumentTypeError('Use a nonnegative integer')
    return value


def main(argv=None):
    examples = requiredExamples()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--example', action='append', choices=[e.identifier for e in examples],
                        help='Run only this ID; repeat to select several')
    parser.add_argument('--execution-budget', type=nonnegative,
                        help='Override every selected execution budget')
    parser.add_argument('--observation-budget', type=nonnegative,
                        help='Override every selected observation budget')
    parser.add_argument('--terms-dir', type=Path, default=Path('demo_terms'))
    parser.add_argument('--inline-terms', action='store_true')
    parser.add_argument('--json', action='store_true', help='Print a structured report')
    args = parser.parse_args(argv)
    results = []
    for example in examples:
        if args.example and example.identifier not in args.example:
            continue
        try:
            result = runExample(example, args.execution_budget,
                                args.observation_budget,
                                None if args.inline_terms else args.terms_dir)
        except Exception as error:
            # A failed example must not hide the remaining demonstrations.
            result = {'id': example.identifier, 'passed': False,
                      'error': f'{type(error).__name__}: {error}'}
        results.append(result)
        if not args.json:
            if 'error' in result:
                print(f"\n{result['id']}: FAIL; {result['error']}")
            else:
                printResult(result)
    passed = sum(result['passed'] for result in results)
    note = 'Budget exhaustion reports a bounded outcome; it does not prove nontermination.'
    if args.json:
        print(json.dumps({'results': results, 'passed': passed,
                          'total': len(results), 'note': note}, indent=2))
    else:
        print(f'\n{passed}/{len(results)} demonstrations passed.')
        print(note)
    return 0 if passed == len(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
