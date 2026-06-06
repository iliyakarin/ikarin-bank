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
        debtor_count = "ACC-DEBT-001"
        creditor_count = "ACC-CRED-002"

        xml_payload = self.parser.create_pacs_008_payload(
            instruction_id, amount, currency, debtor_count, creditor_count
        )

        # Verify XML structure
        root = ET.fromstring(xml_payload)
        self.assertTrue(root.tag.endswith("Document"))
        # The attribute is xmlns, but ET handles the namespace in the tag or via attrib
        self.assertTrue(
            root.tag.startswith("{urn:iso:std:iso:2002_") or 
            "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08" in root.tag or
            "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08" in root.attrib.get("xmlns", "")
        )

        # Find elements (using simplified XPath for simulation)
        # Since the root has a namespace, we must use the namespace in XPath or handle it.
        ns = {'ns': 'urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08'}
        instr_id_elem = root.find(".//ns:InstrId", ns)
        self.assertIsNotNone(instr_id_elem)
        self.assertEqual(instr_id_elem.text, instruction_id)

        amt_elem = root.find(".//ns:Amt", ns)
        self.assertIsNotNone(amt_elem)
        self.assertEqual(amt_elem.text, f"{amount:.2f}")

        curr_elem = root.find(".//ns:Ccy", ns)
        self.assertIsNotNone(curr_elem)
        self.assertEqual(curr_elem.text, currency)

        dbtr_acct_elem = root.find(".//ns:Dbtr/ns:Acct/ns:Id", ns)
        self.assertIsNotNone(dbtr_acct_elem)
        self.assertEqual(dbtr_acct_elem.text, debtor_count)

        cdtr_acct_elem = root.find(".//ns:Cdtr/ns:Acct/ns:Id", ns)
        self.assertIsNotNone(cdtr_acct_elem)
        self.assertEqual(cdtr_acct_elem.text, creditor_count)

    def test_create_pacs_008_payload_invalid_amount(self):
        with self.assertRaises(ValueError) as cm:
            self.parser.create_pacs_008_payload("ID", -10.0, "USD", "A", "B")
        self.assertEqual(str(cm.exception), "Amount must be positive")

    def test_parse_pacs_002_status_mock(self):
        # Test the current stub implementation
        # Note: The parser expects OrgnlGrpId and GrpSts elements
        mock_xml = "<Document xmlns='urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10'><OrgnlGrpId>GRP-123</OrgnlGrpId><GrpSts>processed</GrpSts></Document>"
        result = self.parser.parse_pacs_002_status(mock_xml)
        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["original_group_id"], "GRP-123")

if __name__ == "__main__":
    unittest.main()
