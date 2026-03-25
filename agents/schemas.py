from pydantic import BaseModel, Field
from typing import List, Optional


class ScriptSegment(BaseModel):
    """A single segment/slide of the generated script."""
    segment_id: int = Field(..., description="Sequential segment number")
    narration: str = Field(..., description="Narration text for this segment")
    visual_description: str = Field(
        ..., description="Description of the visual/image for this segment"
    )
    duration_seconds: float = Field(
        ..., description="Estimated duration in seconds for this segment"
    )


class ScriptOutput(BaseModel):
    """Output from the Script Generation Agent."""
    title: str = Field(..., description="Title of the education reel")
    topic: str = Field(..., description="Main topic extracted from transcript")
    content_type: str = Field(
        ...,
        description="Type of content: 'general' or 'maths'. "
        "Use 'maths' for mathematical/formula-heavy content, 'general' for everything else."
    )
    segments: List[ScriptSegment] = Field(
        ..., description="Ordered list of script segments"
    )
    total_duration_seconds: float = Field(
        ..., description="Total estimated duration of the reel"
    )


class TTSSegmentOutput(BaseModel):
    """TTS result for a single segment."""
    segment_id: int = Field(..., description="Matching segment ID from script")
    audio_file_path: str = Field(
        ..., description="Path to the generated audio file"
    )
    duration_seconds: float = Field(
        ..., description="Actual audio duration in seconds"
    )


class TTSOutput(BaseModel):
    """Output from the TTS Agent."""
    audio_segments: List[TTSSegmentOutput] = Field(
        ..., description="List of generated audio segments"
    )
    total_duration_seconds: float = Field(
        ..., description="Total audio duration"
    )


class ImageSegmentOutput(BaseModel):
    """Image generation result for a single segment."""
    segment_id: int = Field(..., description="Matching segment ID from script")
    image_file_path: str = Field(
        ..., description="Path to the generated image file"
    )
    image_prompt_used: str = Field(
        ..., description="The prompt used to generate this image"
    )


class ImageOutput(BaseModel):
    """Output from the Image Generation Agent."""
    images: List[ImageSegmentOutput] = Field(
        ..., description="List of generated images per segment"
    )


class VideoOutput(BaseModel):
    """Output from Video Generation or Manim Video Generation Agent."""
    video_file_path: str = Field(
        ..., description="Path to the final composed video file"
    )
    duration_seconds: float = Field(
        ..., description="Total video duration in seconds"
    )
    resolution: str = Field(
        default="1080x1920", description="Video resolution (portrait for reels)"
    )
    format: str = Field(default="mp4", description="Video file format")
    pipeline_used: str = Field(
        ..., description="Pipeline used: 'general' or 'maths'"
    )
