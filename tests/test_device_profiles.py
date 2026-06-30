import unittest

from backend.app.embedded.device_profiles import get_profile, list_profiles


class DeviceProfileTests(unittest.TestCase):
    def test_lists_expected_profiles(self):
        expected = {
            "raspberry_pi_armv7_32bit",
            "raspberry_pi_arm64",
            "generic_openwrt",
            "antminer_linux",
            "generic_embedded_linux",
            "generic_iot_gateway",
        }
        self.assertTrue(expected.issubset(set(list_profiles())))

    def test_loads_profile(self):
        profile = get_profile("generic_iot_gateway")
        self.assertEqual(profile["name"], "generic_iot_gateway")
        self.assertIn("runtime_targets", profile)


if __name__ == "__main__":
    unittest.main()
