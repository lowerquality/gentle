import unittest

class Base(unittest.TestCase):

    def test_import(self):
        import gentle

    def test_resources(self):
        import gentle
        resources = gentle.Resources()
        import gentle.util.paths
        self.assertNotEqual(gentle.util.paths.get_binary("ext/k3"), "ext/k3")
