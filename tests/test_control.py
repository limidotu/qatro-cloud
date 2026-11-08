from types import SimpleNamespace as NS
import unittest
from scripts.control import operate


def instance(state="STOPPED", **overrides):
    values = dict(lifecycle_state=state, freeform_tags={"qatro-managed": "true"}, shape="VM.Standard.A1.Flex", shape_config=NS(ocpus=2, memory_in_gbs=12))
    values.update(overrides)
    return NS(**values)


class Client:
    def __init__(self, value): self.value, self.calls = value, []
    def get_instance(self, identifier): return NS(data=self.value)
    def instance_action(self, identifier, action):
        self.calls.append((identifier, action))
        return NS(data=instance("STARTING" if action == "START" else "STOPPING"))


class ControlTests(unittest.TestCase):
    def test_start_uses_cloud_power_action(self):
        c = Client(instance()); _, _, changed = operate(c, "test-instance", "start")
        self.assertTrue(changed); self.assertEqual(c.calls, [("test-instance", "START")])

    def test_stop_is_graceful(self):
        c = Client(instance("RUNNING")); operate(c, "test-instance", "stop")
        self.assertEqual(c.calls, [("test-instance", "SOFTSTOP")])

    def test_repeated_start_does_not_restart(self):
        c = Client(instance("RUNNING")); _, _, changed = operate(c, "test-instance", "start")
        self.assertFalse(changed); self.assertEqual(c.calls, [])

    def test_status_cannot_change_power(self):
        c = Client(instance()); operate(c, "test-instance", "status"); self.assertEqual(c.calls, [])

    def test_rejects_unrelated_or_oversized_servers(self):
        for value in [instance(freeform_tags={}), instance(shape="VM.Standard.E5.Flex"), instance(shape_config=NS(ocpus=4, memory_in_gbs=24))]:
            with self.subTest(value=value):
                c = Client(value)
                with self.assertRaises(ValueError): operate(c, "test-instance", "start")
                self.assertEqual(c.calls, [])

    def test_rejects_transitions_and_unknown_actions(self):
        for state, action in [("STOPPING", "start"), ("TERMINATED", "start"), ("RUNNING", "delete")]:
            c = Client(instance(state))
            with self.assertRaises(ValueError): operate(c, "test-instance", action)
            self.assertEqual(c.calls, [])


if __name__ == "__main__": unittest.main()
