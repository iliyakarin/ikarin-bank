import unittest
import asyncio
import xml.etree.ElementTree as ET
from v2.fed_gateway.engine.settlement import SettlementEngine

class TestCamt053Generation(unittest.TestCase):
    def test_camt_053_structure(self):
        """
        Unit Test: Verifies the structure of the generated camt.053 XML.
        """
        engine = SettlementEngine(initial_reserve_balance=1000.0)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            statement_xml = loop.run_until_complete(engine.generate_camt_053_statement(account_id="ACC-123"))
        finally:
            loop.close()

        root = ET.fromstring(statement_xml)
        self.assertEqual(root.tag, "camt.053")
        
        id_elem = root.find("Id")
        self.assertIsNotNone(id_elem)
        self.assertEqual(id_elem.text, "ACC-123")
        
        bal_elem = root.find("Bal")
        self.assertIsNotNone(bal_elem)
        self.assertEqual(float(bal_elem.text), 1000.0)

if __name__ == "__main__":
    unittest.main()
