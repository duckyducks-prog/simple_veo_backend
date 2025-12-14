import pytest
from app.schemas import (
    ImageRequest, VideoRequest, ImageResponse, 
    AssetResponse, UpscaleRequest
)

class TestImageRequest:
    def test_minimal_request(self):
        """Only prompt required"""
        req = ImageRequest(prompt="a puppy")
        assert req.prompt == "a puppy"
        assert req.aspect_ratio == "1:1"
        assert req.reference_images is None

    def test_full_request(self):
        """All fields populated"""
        req = ImageRequest(
            prompt="a cat",
            reference_images=["base64data"],
            aspect_ratio="16:9",
            resolution="2K"
        )
        assert req.aspect_ratio == "16:9"
        assert len(req.reference_images) == 1

    def test_missing_prompt_fails(self):
        """Prompt is required"""
        with pytest.raises(ValueError):
            ImageRequest()

class TestVideoRequest:
    def test_defaults(self):
        """Check default values"""
        req = VideoRequest(prompt="dancing cat")
        assert req.duration_seconds == 8
        assert req.generate_audio is True
        assert req.aspect_ratio == "16:9"

class TestUpscaleRequest:
    def test_valid_upscale_factors(self):
        """Accepts valid upscale factors"""
        for factor in ["x2", "x3", "x4"]:
            req = UpscaleRequest(image="base64", upscale_factor=factor)
            assert req.upscale_factor == factor

class TestAssetResponse:
    def test_full_response(self):
        """Asset response with all fields"""
        resp = AssetResponse(
            id="abc-123",
            url="https://storage.googleapis.com/bucket/image.png",
            asset_type="image",
            prompt="a puppy",
            created_at="2024-01-01T00:00:00Z",
            mime_type="image/png",
            user_id="user-456"
        )
        assert resp.id == "abc-123"
        assert resp.asset_type == "image"