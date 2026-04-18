import unittest

from plc_ascii.protocol import decode_message, encode_message, hello_message


class ProtocolTests(unittest.TestCase):
    def test_protocol_round_trip(self) -> None:
        payload = hello_message("host")
        self.assertEqual(decode_message(encode_message(payload)), payload)


if __name__ == "__main__":
    unittest.main()
