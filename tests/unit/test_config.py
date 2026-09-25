import os
import unittest
from unittest.mock import patch

from knowledge_assistant.config import get_chroma_path


class ChromaPathTests(unittest.TestCase):
    def test_uses_d_drive_default_when_chroma_path_is_not_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_chroma_path(), r"D:\ChromaDB")

    def test_uses_configured_chroma_path(self):
        with patch.dict(os.environ, {"CHROMA_PATH": r"D:\CustomChroma"}, clear=True):
            self.assertEqual(get_chroma_path(), r"D:\CustomChroma")
