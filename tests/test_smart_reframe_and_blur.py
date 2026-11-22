from services.object_blur_service import ObjectTrackingBlurService, TrackingResult
from services.smart_reframe_service import SmartReframeService


def test_smart_reframe_crop_dimensions():
    service = SmartReframeService(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe")
    # Mock dimensions probe
    service.probe_dimensions = lambda p: (1920, 1080, 12.0)

    # 9:16 vertical crop of 1920x1080
    res = service.analyze_reframe("/fake/video.mp4", target_aspect="9:16")
    assert res.aspect_ratio == "9:16"
    assert res.crop_h == 1080
    assert res.crop_w == 608  # 1080 * 9 / 16 rounded to even
    assert "crop=608:1080:" in res.filter_expr


def test_smart_reframe_aspect_1_to_1():
    service = SmartReframeService(ffmpeg_path="ffmpeg", ffprobe_path="ffprobe")
    service.probe_dimensions = lambda p: (1920, 1080, 10.0)

    res = service.analyze_reframe("/fake/video.mp4", target_aspect="1:1")
    assert res.crop_w == 1080
    assert res.crop_h == 1080
    assert "crop=1080:1080:" in res.filter_expr


def test_object_blur_service_filter_generation():
    service = ObjectTrackingBlurService(ffmpeg_path="ffmpeg")
    result = TrackingResult(
        target_type="face",
        blur_style="box",
        average_box=(200, 150, 120, 120),
    )

    box_filter = service.build_ffmpeg_blur_filter(result, blur_strength=15)
    assert "boxblur=15:5" in box_filter
    assert "crop=120:120:200:150" in box_filter

    result.blur_style = "pixelate"
    pix_filter = service.build_ffmpeg_blur_filter(result)
    assert "flags=neighbor" in pix_filter

    result.blur_style = "gaussian"
    gblur_filter = service.build_ffmpeg_blur_filter(result, blur_strength=20)
    assert "gblur=sigma=20" in gblur_filter
