import contextlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path

providers = types.ModuleType('providers')
providers.__path__ = []
providers.register_provider = lambda profile: None
base = types.ModuleType('providers.base')
base.ProviderProfile = type('ProviderProfile', (), {'__init__': lambda self, **kwargs: None})
agent = types.ModuleType('agent')
agent.__path__ = []
acp = types.ModuleType('agent.copilot_acp_client')

class FakeACP:
    response_model = 'opencode/deepseek-v4.1-flash-free'
    available = True
    calls = []
    def __init__(self, **kwargs): pass
    @contextlib.contextmanager
    def _session(self, timeout):
        yield {'sessionId': 'test'}, self.request
    def request(self, method, params, **kwargs):
        self.calls.append(method)
        if method == 'session/set_config_option':
            return {'configOptions': [{'id': 'model', 'currentValue': self.response_model}]}
        kwargs['text_parts'].append('ok')

acp.CopilotACPClient = FakeACP
acp._model_selection_request = lambda session, model: ('session/set_config_option', {}) if FakeACP.available else None
sys.modules.update({'providers': providers, 'providers.base': base, 'agent': agent, 'agent.copilot_acp_client': acp})
spec = importlib.util.spec_from_file_location('safe_acp', Path(__file__).parent / '__init__.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SafeModelTests(unittest.TestCase):
    def setUp(self):
        FakeACP.calls = []
        FakeACP.available = True
        FakeACP.response_model = module._FREE_MODEL
        self.client = module.opencode_acp.create_client()

    def test_confirmed_free_model_can_receive_prompt(self):
        self.assertEqual(self.client._run_prompt('test', timeout_seconds=2, model=module._FREE_MODEL), ('ok', ''))
        self.assertEqual(FakeACP.calls, ['session/set_config_option', 'session/prompt'])

    def test_confirmed_glm_model_can_receive_prompt(self):
        FakeACP.response_model = module._GLM_MODEL
        self.assertEqual(self.client._run_prompt('test', timeout_seconds=2, model='glm-5.3-flash-free'), ('ok', ''))
        self.assertEqual(FakeACP.calls, ['session/set_config_option', 'session/prompt'])

    def test_paid_model_is_rejected(self):
        with self.assertRaises(ValueError): self.client._run_prompt('test', timeout_seconds=2, model='opencode/paid')
        self.assertEqual(FakeACP.calls, [])

    def test_unavailable_model_is_rejected(self):
        FakeACP.available = False
        with self.assertRaises(RuntimeError): self.client._run_prompt('test', timeout_seconds=2, model=module._FREE_MODEL)
        self.assertEqual(FakeACP.calls, [])

    def test_unconfirmed_model_is_rejected_before_prompt(self):
        FakeACP.response_model = 'opencode/paid'
        with self.assertRaises(RuntimeError): self.client._run_prompt('test', timeout_seconds=2, model=module._FREE_MODEL)
        self.assertEqual(FakeACP.calls, ['session/set_config_option'])

if __name__ == '__main__': unittest.main()
