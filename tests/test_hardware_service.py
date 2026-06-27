import unittest

from services.hardware_service import HardwareCapabilities, HardwareService


class HardwareCapabilitiesTest(unittest.TestCase):
    def test_no_gpu_defaults(self) -> None:
        caps = HardwareCapabilities()
        self.assertFalse(caps.has_gpu)
        self.assertEqual(caps.best_vendor, "cpu")
        self.assertIn("CPU", caps.summary())

    def test_nvidia_detection(self) -> None:
        caps = HardwareCapabilities(
            nvidia_available=True,
            nvidia_encoders=["h264_nvenc", "hevc_nvenc"],
        )
        self.assertTrue(caps.has_gpu)
        self.assertEqual(caps.best_vendor, "nvidia")
        self.assertIn("NVIDIA", caps.summary())

    def test_intel_detection(self) -> None:
        caps = HardwareCapabilities(
            intel_qsv_available=True,
            qsv_encoders=["h264_qsv"],
        )
        self.assertTrue(caps.has_gpu)
        self.assertEqual(caps.best_vendor, "intel")

    def test_amd_detection(self) -> None:
        caps = HardwareCapabilities(
            amd_amf_available=True,
            amf_encoders=["h264_amf"],
        )
        self.assertTrue(caps.has_gpu)
        self.assertEqual(caps.best_vendor, "amd")


class HardwareServiceTest(unittest.TestCase):
    def test_no_ffmpeg_path(self) -> None:
        service = HardwareService()
        caps = service.detect()
        self.assertFalse(caps.has_gpu)
        self.assertIn("not set", caps.detection_error)

    def test_cache_is_used(self) -> None:
        service = HardwareService()
        caps1 = service.detect()
        caps2 = service.detect()
        self.assertIs(caps1, caps2)

    def test_invalidate_cache(self) -> None:
        service = HardwareService()
        service.detect()
        self.assertIsNotNone(service.cached)
        service.invalidate_cache()
        self.assertIsNone(service.cached)


if __name__ == "__main__":
    unittest.main()
