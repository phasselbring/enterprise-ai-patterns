import unittest
from unittest.mock import patch
from types import SimpleNamespace
from model_config import model_for
from agent_runner import extract_trace
from compare_models import evaluate


class EvaluationTests(unittest.TestCase):
    def test_provider_selection(self):
        for provider, env, model in [('openai', 'OPENAI_API_KEY', 'openai:gpt-4.1-mini'),
                                     ('claude', 'ANTHROPIC_API_KEY', 'anthropic:claude-sonnet-4-5'),
                                     ('gemini', 'GOOGLE_API_KEY', 'google_genai:gemini-2.5-flash')]:
            with patch.dict('os.environ', {env: 'dummy', f'{provider.upper()}_AGENT_MODEL': ''}):
                # Empty override is treated as absent in the implementation below.
                self.assertTrue(model_for(provider).startswith(model.split(':')[0] + ':'))

    def test_invalid_provider(self):
        with self.assertRaises(ValueError):
            model_for('unsupported')

    def test_missing_key(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(RuntimeError):
                model_for('openai')

    def test_trace_correlates_calls_and_results(self):
        model_message = SimpleNamespace(tool_calls=[{'id': 'a1', 'name': 'lookup_order', 'args': {'order_id': 'SO-1001'}}])
        tool_message = SimpleNamespace(tool_calls=[], tool_call_id='a1', content='{"order_id":"SO-1001"}', status='success')
        trace = extract_trace([model_message, tool_message])
        self.assertEqual(trace[0]['name'], 'lookup_order')
        self.assertEqual(trace[0]['args']['order_id'], 'SO-1001')
        self.assertIn('SO-1001', trace[0]['result'])

    def test_scorecard_requires_tool_evidence(self):
        run = {'order_id': 'SO-1001', 'error': None, 'response': '22 units short, approval required; draft only', 'tool_trace': []}
        score = evaluate(run)
        self.assertFalse(score['checks']['lookup_called'])
        self.assertFalse(score['checks']['shortage_tool_called'])

    def test_failed_run_is_not_complete(self):
        score = evaluate({'order_id': 'SO-1001', 'error': 'timeout', 'response': '', 'tool_trace': []})
        self.assertFalse(score['checks']['completed'])


if __name__ == '__main__':
    unittest.main()
