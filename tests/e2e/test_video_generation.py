"""E2E tests for video generation - COSTS MONEY AND TAKES TIME"""
import pytest
import time


@pytest.mark.e2e
class TestVideoGenerationE2E:
    """E2E tests for video generation - WARNING: Very slow and expensive"""
    
    def test_generate_video_with_polling(self, api_base_url, auth_headers, http_client):
        """Generate a video and poll until completion - SLOW (2-5 minutes)"""
        # Start video generation
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "a small red ball bouncing once",  # Simple = faster
                "duration_seconds": 4,  # Shortest duration
                "aspect_ratio": "16:9"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return operation name for polling
        assert data["status"] == "processing"
        assert "operation_name" in data
        operation_name = data["operation_name"]
        
        print(f"\n🎬 Video generation started: {operation_name}")
        
        # Poll for completion (max 5 minutes)
        max_attempts = 60  # 5 minutes with 5-second intervals
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            time.sleep(5)  # Wait 5 seconds between polls
            
            status_response = http_client.post(
                f"{api_base_url}/generate/video/status",
                headers=auth_headers,
                json={
                    "operation_name": operation_name,
                    "prompt": "a small red ball bouncing once"
                }
            )
            
            assert status_response.status_code == 200
            status_data = status_response.json()
            
            print(f"⏳ Poll attempt {attempt}: Status = {status_data.get('status')}, Progress = {status_data.get('progress', 0)}%")
            
            if status_data["status"] == "complete":
                print(f"✅ Video generation complete!")
                print(f"Response keys: {list(status_data.keys())}")
                
                # Check if we got video data
                has_video = status_data.get("video_base64") or status_data.get("storage_uri")
                
                if not has_video:
                    print(f"❌ Video marked as complete but no video data found!")
                    print(f"Available fields: {list(status_data.keys())}")
                    pytest.fail("Video generation completed but no video data returned")
                
                # Verify we got either base64 or URI
                assert has_video, "Video should have either video_base64 or storage_uri"
                
                if status_data.get("video_base64"):
                    print(f"📦 Got video as base64 (length: {len(status_data['video_base64'])})")
                if status_data.get("storage_uri"):
                    print(f"🔗 Got storage URI: {status_data['storage_uri']}")
                
                return  # Success!
            
            elif status_data["status"] == "error":
                error_msg = status_data.get('error', {})
                print(f"❌ Video generation failed: {error_msg}")
                
                # If it's an internal error from Google, skip instead of fail
                if isinstance(error_msg, dict) and error_msg.get('code') == 13:
                    pytest.skip(f"Google API internal error (temporary): {error_msg.get('message')}")
                else:
                    pytest.fail(f"Video generation failed: {error_msg}")
        
        pytest.fail(f"Video generation timed out after {max_attempts} attempts")
    
    def test_unauthorized_video_request(self, api_base_url, http_client):
        """Request without token returns 401"""
        response = http_client.post(
            f"{api_base_url}/generate/video",
            json={"prompt": "test"}
        )
        
        assert response.status_code == 401


@pytest.mark.e2e
class TestVideoGenerationWithSeedE2E:
    """E2E tests for video generation with seed data for reproducibility"""
    
    def test_video_generation_with_seed_parameter(self, api_base_url, auth_headers, http_client, seed_values):
        """Verify seed parameter is accepted in video generation request"""
        seed_value = seed_values["seed_1"]
        
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "a simple animation with consistent style",
                "seed": seed_value,
                "duration_seconds": 4,
                "aspect_ratio": "16:9"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify generation started successfully with seed
        assert data["status"] == "processing"
        assert "operation_name" in data
        print(f"✓ Video generation with seed {seed_value} started: {data['operation_name']}")
    
    def test_video_generation_with_zero_seed(self, api_base_url, auth_headers, http_client, seed_values):
        """Verify zero seed value is handled correctly"""
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "test animation",
                "seed": seed_values["seed_zero"],
                "duration_seconds": 4,
                "aspect_ratio": "16:9"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        print(f"✓ Video generation with seed 0 accepted")
    
    def test_video_generation_with_large_seed(self, api_base_url, auth_headers, http_client):
        """Verify large seed values are handled correctly"""
        large_seed = 2147483647  # Max 32-bit signed int
        
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "test animation",
                "seed": large_seed,
                "duration_seconds": 4,
                "aspect_ratio": "16:9"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        print(f"✓ Video generation with large seed {large_seed} accepted")
    
    def test_video_generation_without_seed(self, api_base_url, auth_headers, http_client):
        """Verify video generation still works when seed is not provided (randomized)"""
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "random style animation",
                "duration_seconds": 4,
                "aspect_ratio": "16:9"
                # No seed provided - should use random generation
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        print(f"✓ Video generation without seed (randomized) started")
    
    def test_video_generation_with_null_seed(self, api_base_url, auth_headers, http_client):
        """Verify null seed is treated as no seed (randomized generation)"""
        response = http_client.post(
            f"{api_base_url}/generate/video",
            headers=auth_headers,
            json={
                "prompt": "animation",
                "seed": None,
                "duration_seconds": 4,
                "aspect_ratio": "16:9"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        print(f"✓ Video generation with null seed accepted")

