import re

class ABAValidator:
    """
    Validator for American Bankers Association (ABA) routing numbers.
    Implements the checksum verification algorithm.
    """
    
    @staticmethod
    def validate_checksum(routing_number: str) -> bool:
        """
        Validates the ABA routing number using the checksum algorithm.
        Formula: 3(d1 + d4 + d_7) + 7(d2 + d5 + d8) + (d3 + d6 + d9) mod 10 == 0
        """
        if not re.match(r"^\d{9}$", routing_number):
            return False
            
        digits = [int(d) for d in routing_number]
        
        checksum = (
            3 * (digits[0] + digits[3] + digits[6]) +
            7 * (digits[1] + digits[4] + digits[7]) +
            (digits[2] + digits[5] + digits[8])
        )
        
        return checksum % 10 == 0

    @staticmethod
    def validate_format(routing_number: str) -> bool:
        """Checks if the routing number is exactly 9 digits."""
        return bool(re.match(r"^\d{9}$", routing_number))
