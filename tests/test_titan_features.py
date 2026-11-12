import os
import tempfile
import unittest
from unittest.mock import patch

import user_memory
from agent import _calculate

class AgentCalculatorTests(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(_calculate("(125 * 8) / 5"), 200)

    def test_rejects_code_execution(self):
        with self.assertRaises(ValueError):
            _calculate("__import__('os').system('echo unsafe')")

    def test_rejects_huge_exponent(self):
        with self.assertRaises(ValueError):
            _calculate("2 ** 101")

class PrivateMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = user_memory.DB_PATH
        user_memory.DB_PATH = os.path.join(self.temp.name, "test.sqlite3")

    def tearDown(self):
        user_memory.DB_PATH = self.old_path
        self.temp.cleanup()

    def test_memory_is_isolated_by_account(self):
        with patch.object(user_memory, "_email_from_token", side_effect=lambda token: token):
            user_memory.save_memory(user_memory.MemoryCreate(content="Likes concise answers"), "alice@example.com")
            user_memory.save_memory(user_memory.MemoryCreate(content="Likes detailed answers"), "bob@example.com")
            alice = user_memory.get_memory_context("alice@example.com")
            bob = user_memory.get_memory_context("bob@example.com")
        self.assertIn("concise", alice)
        self.assertNotIn("detailed", alice)
        self.assertIn("detailed", bob)
        self.assertNotIn("concise", bob)

    def test_duplicate_memory_is_not_duplicated(self):
        with patch.object(user_memory, "_email_from_token", return_value="alice@example.com"):
            first = user_memory.save_memory(user_memory.MemoryCreate(content="  Likes   robotics "), "token")
            second = user_memory.save_memory(user_memory.MemoryCreate(content="Likes robotics"), "token")
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])

if __name__ == "__main__":
    unittest.main()
