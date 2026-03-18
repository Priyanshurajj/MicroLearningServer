"""
image_service.py - Orchestrates AI image generation for video slides.

Handles generating scene background images for each slide and the
teacher character image, using the Gemini image generation API.
"""

import os
from pathlib import Path
from gemini_service import generate_image, generate_teacher_image


def generate_slide_images(slides: list, output_dir: str) -> list[str | None]:
    """Generate AI background images for each slide.

    Args:
        slides: List of slide dicts, each with an 'image_prompt' key.
        output_dir: Directory to save generated images.

    Returns:
        List of image file paths (None for any failed generations).
    """
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []

    for i, slide in enumerate(slides):
        prompt = slide.get("image_prompt", f"Educational illustration about {slide.get('title', 'learning')}")

        # Append style hints for consistency
        full_prompt = (
            f"{prompt}. "
            "High quality, 16:9 landscape aspect ratio, no text or words in the image, "
            "suitable as a video background, vibrant and visually rich."
        )

        save_path = os.path.join(output_dir, f"slide_{i + 1}.png")
        result = generate_image(full_prompt, save_path)
        image_paths.append(result)

        if result:
            print(f"[IMAGE] Slide {i + 1}/{len(slides)}: Generated ✓")
        else:
            print(f"[IMAGE] Slide {i + 1}/{len(slides)}: FAILED ✗")

    successful = sum(1 for p in image_paths if p is not None)
    print(f"[IMAGE] Generated {successful}/{len(slides)} slide images.")
    return image_paths


def generate_teacher(output_dir: str) -> str | None:
    """Generate or reuse a teacher character image.

    The teacher image is generated once and cached in the output directory.
    Subsequent calls with the same output_dir will reuse the existing image.

    Args:
        output_dir: Directory to save/find the teacher image.

    Returns:
        Path to the teacher image, or None if generation failed.
    """
    os.makedirs(output_dir, exist_ok=True)
    teacher_path = os.path.join(output_dir, "teacher.png")

    # Reuse if already generated
    if os.path.exists(teacher_path):
        print(f"[IMAGE] Teacher image already exists: {teacher_path}")
        return teacher_path

    result = generate_teacher_image(teacher_path)
    if result:
        print(f"[IMAGE] Teacher image generated: {teacher_path}")
    else:
        print(f"[IMAGE] Teacher image generation FAILED.")
    return result
