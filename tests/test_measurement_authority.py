import unittest
from unittest.mock import patch

from verantis_mcp.server import _label_measurement_authority, call_tool


class MeasurementAuthorityTest(unittest.TestCase):
    def test_labels_wallet_activity_without_reclassifying_values(self):
        entity = {
            "host": "example.test",
            "rails": [{
                "payments": 48,
                "buyers": 13,
                "repeat": 0.462,
                "volume_usd": 11.1213,
            }],
        }

        result = _label_measurement_authority(entity)

        rail = result["rails"][0]
        self.assertEqual(rail["payments"], 48)
        self.assertEqual(rail["buyers"], 13)
        self.assertEqual(rail["activity_scope"], "recipient_wallet_inbound")
        self.assertEqual(rail["service_attribution"], "unresolved")
        self.assertIn("recipient-wallet", result["measurement_notice"])

    def test_preserves_stronger_backend_authority(self):
        entity = {
            "rails": [{
                "payments": 2,
                "activity_scope": "operation_bound_settlements",
                "service_attribution": "seller_receipt",
            }],
        }

        result = _label_measurement_authority(entity)

        rail = result["rails"][0]
        self.assertEqual(rail["activity_scope"], "operation_bound_settlements")
        self.assertEqual(rail["service_attribution"], "seller_receipt")

    def test_ignores_records_without_wallet_activity(self):
        entity = {"host": "example.test", "rails": [{"price_usd": 0.01}]}

        result = _label_measurement_authority(entity)

        self.assertNotIn("measurement_notice", result)
        self.assertNotIn("activity_scope", result["rails"][0])
        self.assertNotIn("service_attribution", result["rails"][0])

    def test_preserves_non_entity_values(self):
        self.assertEqual(_label_measurement_authority(None), None)
        self.assertEqual(_label_measurement_authority([]), [])

    @patch("verantis_mcp.server._api_get")
    def test_find_paid_service_labels_each_result(self, api_get):
        api_get.return_value = {
            "entities": [{"host": "example.test", "rails": [{"buyers": 3}]}],
            "data_generated_at": "2026-08-29T00:00:00Z",
        }

        result = call_tool("find_paid_service", {"query": "example"})

        rail = result["results"][0]["rails"][0]
        self.assertEqual(rail["activity_scope"], "recipient_wallet_inbound")
        self.assertEqual(rail["service_attribution"], "unresolved")

    @patch("verantis_mcp.server._api_get")
    def test_get_service_labels_result(self, api_get):
        api_get.return_value = {
            "host": "example.test",
            "rails": [{"payments": 4, "volume_usd": 0.04}],
        }

        result = call_tool("get_service", {"domain": "example.test"})

        self.assertEqual(result["rails"][0]["activity_scope"], "recipient_wallet_inbound")
        self.assertIn("measurement_notice", result)


if __name__ == "__main__":
    unittest.main()
