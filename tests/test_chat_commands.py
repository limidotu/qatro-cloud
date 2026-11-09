import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'scripts/register_chat_commands.py'
spec = importlib.util.spec_from_file_location('register_chat_commands', MODULE)
chat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chat)


class ChatRegistrationTest(unittest.TestCase):
    def test_adds_only_requested_commands_without_deleting_others(self):
        calls = []
        def fake_request(token, path, data=None):
            calls.append((path, data))
            if path == 'applications/@me': return {'id': 'app'}
            if data is None: return [{'name': 'unrelated', 'type': 1}]
            return data
        with patch.object(chat, 'request', side_effect=fake_request):
            chat.reconcile('example', apply=True)
        writes = [item for _, item in calls if item is not None]
        self.assertEqual({item['name'] for item in writes}, {'new', 'title', 'sessions', 'resume'})
        self.assertEqual(len(writes), 4)

    def test_refuses_to_overwrite_an_existing_command(self):
        def fake_request(token, path, data=None):
            if data is not None: self.fail('Should not change existing commands')
            return {'id': 'app'} if path == 'applications/@me' else [{'name': 'new', 'type': 1}]
        with patch.object(chat, 'request', side_effect=fake_request):
            with self.assertRaises(RuntimeError): chat.reconcile('example', apply=True)


if __name__ == '__main__':
    unittest.main()
