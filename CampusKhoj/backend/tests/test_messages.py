import unittest
from backend.message_templates import render_message, mask_phone, TEMPLATES

class TestMessageTemplates(unittest.TestCase):
    def test_mask_phone(self):
        self.assertEqual(mask_phone("9876543210"), "98****3210")
        self.assertEqual(mask_phone("+919876543210"), "98****3210")
        self.assertEqual(mask_phone(""), "No phone saved (preview only)")
        self.assertEqual(mask_phone(None), "No phone saved (preview only)")
        self.assertEqual(mask_phone("1234"), "****1234")

    def test_templates_never_leak_private_fields(self):
        context = {
            "item_name": "Casio Calculator",
            "score": 85,
            "claim_id": 42,
            "question": "What color is the pouch?",
            "campus_name": "Kondhwa",
            # Malicious/sensitive fields that must NEVER appear in formatted output
            "private_details": "Secret engraved code 998877",
            "expected_evidence": "Passcode 1234",
            "prn": "1251070099",
            "other_student_prn": "1251070088"
        }

        for code in TEMPLATES:
            msg = render_message(code, context)
            self.assertNotIn("Secret engraved code 998877", msg)
            self.assertNotIn("Passcode 1234", msg)
            self.assertNotIn("1251070099", msg)
            self.assertNotIn("1251070088", msg)
            self.assertNotIn("AI", msg)
            self.assertTrue(len(msg) <= 480, f"Message {code} exceeds 480 chars: len={len(msg)}")

    def test_template_codes_exist(self):
        expected_codes = [
            "MATCH_FOUND",
            "CLAIM_SUBMITTED",
            "QUESTION_ASKED",
            "CLAIM_APPROVED",
            "CLAIM_REJECTED",
            "HANDOVER_REMINDER",
            "HANDOVER_COMPLETED",
            "DOUBLE_VERIFICATION"
        ]
        for c in expected_codes:
            self.assertIn(c, TEMPLATES)

if __name__ == "__main__":
    unittest.main()
