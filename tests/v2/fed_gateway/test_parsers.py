import unittest
import xml.etree.ElementTree as ET
from v2.fed_gateway.parsers.iso20022 import ISO20022Parser

class TestISO20022Parser(unittest.TestCase):
    def setUp(self):
        self.parser = ISO20022Parser()

    def test_create_pacs_008_payload_success(self):
        instruction_id = "ABC-12345"
        amount = 1500.50
        currency = "USD"
        debtor_account = "ACC-DEBT-001"
        creditor_account = "ACC-CRED-002"

        xml_payload = self.parser.create_pacs_008_payload(
            instruction_id, amount, currency, debtor_account, creditor_account
        )

        # Verify XML structure
        root = ET.fromstring(xml_payload)
        self.assertTrue(root.tag.endswith("Document"))
        self.assertIn("urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08", root.attrib.get("xmlns", ""))


        self.assertIn("urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08", root.attrib.get("xmlns", ""))

        # Find elements (using simplified XPath for simulation)
        instr_id_elem = root.find(".//InstrId")
        self.assertIsNotNone(instr_id_elem)
        self.assertEqual(instr_id_elem.text, instruction_id)

        amt_elem = root.find(".//Amt")
        self.assertIsNotNone(amt_elem)
        self.assertEqual(amt_elem.text, "1500.50")

        curr_elem = root.find(".//Ccy")
        self.assertIsNotNone(curr_elem)
        self.assertEqual(curr_elem.text, currency)

        dbtr_acct_elem = root.find(".//Dbtr/Acct/Id")
        self.assertIsNotNone(dbtr_acct_elem)
        self.assertEqual(dbtr_acct_elem.text, debtor_account)

        cdtr_acct_elem = root.find(".//Cdtr/Acct/Id")
        self.assertIsNotNone(cdtr_acct_elem)
        self.assertEqual(cdtr_acct_elem.text, creditor_account)

    def test_create_pacs_008_payload_invalid_amount(self):
        with self.assertRaises(ValueError) as cm:
            self.parser.create_pacs_008_payload("ID", -10.0, "USD", "A", "B")
        self.assertEqual(str(cm.exception), "Amount must be positive")

    def test_parse_pacs_002_status_mock(self):
        # Test the current stub implementation
        mock_xml = "<Document xmlns='urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10'><Status>processed</Status></Document>"
        result = self.parser.parse_pacs_002_status(mock_xml)
        self.assertEqual(result["status"], "processed")

if __name__ == "__main__":
    unittest.main()
