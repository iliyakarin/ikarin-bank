import re
import xml.etree.ElementTree as ET
from datetime import datetime

class ISO20022Parser:
    """
    Handles serialization and deserialization of ISO 20022 XML messages.
    Implements lightweight XML utility helpers for token efficiency.
    """

    def create_pacs_008_payload(
        self, 
        instruction_id: str, 
        amount: float, 
        currency: str, 
        debtor_account: str, 
        creditor_account: str
    ) -> str:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Root element for pacs.008
        root = ET.Element("Document", xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08")
        
        # Financial Institution Information
        fi_info = ET.SubElement(root, "FIToFICstmrCdtTrf")
        
        # Instruction ID
        instr_id = ET.SubElement(fi_info, "InstrId")
        instr_id.text = instruction_id
        
        # Amount and Currency
        amt = ET.SubElement(fi_info, "Amt")
        amt.text = f"{amount:.2f}"
        
        curr = ET.SubElement(fi_info, "Ccy")
        curr.text = currency
        
        # Debtor/Creditor (Simplified for simulation)
        debtor = ET.SubElement(fi_info, "Dbtr")
        dbtr_acct = ET.SubElement(debtor, "Acct")
        acct_id = ET.SubElement(dbtr_acct, "Id")
        acct_id.text = debtor_account
        
        creditor = ET.SubElement(fi_info, "Cdtr")
        cr_int_acct = ET.SubElement(creditor, "Acct")
        cr_acct_id = ET.SubElement(cr_int_acct, "Id")
        cr_acct_id.text = creditor_account
        
        return ET.tostring(root, encoding="unicode")

    def create_pacs_002_payload(
        self,
        instruction_id: str,
        status: str,
        original_group_id: str,
        reason: str = ""
    ) -> str:
        """
        Creates a pacs.002 Payment Status Report XML payload.
        """
        root = ET.Element("Document", xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10")
        fi_info = ET.SubElement(root, "FIToFICstmrCdtTrf")
        
        grp_id = ET.SubElement(fi_info, "OrgnlGrpId")
        grp_id.text = original_group_id
        
        grp_sts = ET.SubElement(fi_info, "GrpSts")
        grp_sts.text = status
        
        if reason:
            reason_elem = ET.SubElement(fi_info, "Reason")
            reason_elem.text = reason

        return ET.tostring(root, encoding="unicode")

    def parse_pacs_002_status(self, xml_string: str) -> dict:
        """
        Parses a pacs.002 Payment Status Report.
        Returns a dictionary containing the original group ID and the group status.
        """
        root = ET.fromstring(xml_string)
        
        # Determine namespace from the root tag or default to a standard one
        ns_match = re.search(r'\{(.+)\}', root.tag)
        ns = {'ns': ns_match.group(1)} if ns_match else {}

        # Extracting key fields using the namespace
        grp_id_elem = root.find(".//ns:OrgnlGrpId", ns) if ns else root.find(".//OrgnlGrpId")
        grp_sts_elem = root.find(".//ns:GrpSts", ns) if ns else root.find(".//GrpSts")
        if grp_sts_elem is None:
            grp_sts_elem = root.find(".//ns:Status", ns) if ns else root.find(".//Status")

        return {
            "original_group_id": grp_id_elem.text if grp_id_elem is not None else None,
            "status": grp_sts_elem.text if grp_sts_elem is not None else "UNKNOWN"
        }
