import json
import os
import logging

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from PIL import Image, ImageDraw, ImageFont

from .config import ROUTING_MODEL, OUTPUT_DIR, OVERLAY_FONT_PATH

logger = logging.getLogger("EduReelADK")

# Concept map overlay dimensions (placed top-right corner)
MAP_W = 240
MAP_H = 400
PADDING = 12
NODE_H = 36
NODE_RADIUS = 6

ACTIVE_COLOR = (255, 220, 0, 230)      # Yellow for active topic
INACTIVE_COLOR = (160, 160, 160, 180)  # Gray for inactive topics
BG_COLOR = (0, 0, 0, 170)             # Dark semi-transparent background
ACTIVE_TEXT = (20, 20, 20, 255)        # Dark text on yellow
INACTIVE_TEXT = (210, 210, 210, 255)   # Light text on dark
CONNECTOR_COLOR = (100, 100, 100, 180) # Connector lines between nodes
BORDER_COLOR = (80, 80, 80, 200)       # Border around map


def generate_concept_map_frames(tool_context: ToolContext) -> dict:
    """Generates one concept map PNG per segment and stores paths in state."""
    enhanced_json = tool_context.state.get("enhanced_script", "")
    if not enhanced_json:
        enhanced_json = tool_context.state.get("script_output", "")

    try:
        script = json.loads(enhanced_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Concept Map Agent: Cannot parse script: {e}")
        return {"status": "error", "error": str(e)}

    run_id = script.get("run_id", "default")
    map_dir = os.path.join(OUTPUT_DIR, run_id, "concept_map")
    os.makedirs(map_dir, exist_ok=True)

    segments = sorted(script.get("segments", []), key=lambda s: s["segment_id"])
    if not segments:
        result = {"run_id": run_id, "frames": {}}
        tool_context.state["concept_map_output"] = json.dumps(result)
        return {"status": "success", "concept_map_output": json.dumps(result)}

    # Extract topic labels: first 4 words of narration
    topic_labels = []
    for seg in segments:
        narration = seg.get("narration", "")
        words = narration.split()
        label = " ".join(words[:4]) + ("..." if len(words) > 4 else "")
        topic_labels.append((seg["segment_id"], label))

    # Load font
    try:
        font_active = ImageFont.truetype(OVERLAY_FONT_PATH, 14)
        font_inactive = ImageFont.truetype(OVERLAY_FONT_PATH, 13)
    except (OSError, IOError):
        font_active = ImageFont.load_default()
        font_inactive = ImageFont.load_default()

    frames = {}
    for active_idx, active_seg in enumerate(segments):
        active_id = active_seg["segment_id"]
        out_path = os.path.join(map_dir, f"frame_{active_id}.png")

        img = _render_concept_map(
            topic_labels, active_idx, font_active, font_inactive
        )
        img.save(out_path, "PNG")
        frames[str(active_id)] = os.path.abspath(out_path)

    result = {"run_id": run_id, "frames": frames}
    concept_map_json = json.dumps(result)
    tool_context.state["concept_map_output"] = concept_map_json

    logger.info(f"Concept Map Agent: {len(frames)} frames generated")
    return {"status": "success", "concept_map_output": concept_map_json}


def _render_concept_map(
    topic_labels: list,
    active_idx: int,
    font_active: ImageFont.FreeTypeFont,
    font_inactive: ImageFont.FreeTypeFont,
) -> Image.Image:
    """Renders a concept map overlay image with the active topic highlighted."""
    img = Image.new("RGBA", (MAP_W, MAP_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded rect
    draw.rounded_rectangle(
        [0, 0, MAP_W - 1, MAP_H - 1],
        radius=10,
        fill=BG_COLOR,
        outline=BORDER_COLOR,
        width=1,
    )

    # Title
    title = "Topics"
    try:
        title_font = ImageFont.truetype(OVERLAY_FONT_PATH, 13)
    except (OSError, IOError):
        title_font = ImageFont.load_default()

    draw.text((PADDING, PADDING - 2), title, font=title_font, fill=(200, 200, 200, 200))

    # Calculate visible topics (scrolling window of up to 9 nodes)
    max_visible = min(len(topic_labels), 9)
    start = max(0, active_idx - max_visible // 2)
    start = min(start, max(0, len(topic_labels) - max_visible))
    visible = topic_labels[start: start + max_visible]

    y = PADDING + 22  # Below title

    for i, (seg_id, label) in enumerate(visible):
        global_idx = start + i
        is_active = global_idx == active_idx

        # Connector line from previous node
        if i > 0:
            connector_y = y - 6
            draw.line(
                [(PADDING + NODE_RADIUS, connector_y - 4),
                 (PADDING + NODE_RADIUS, connector_y)],
                fill=CONNECTOR_COLOR,
                width=1,
            )

        node_rect = [PADDING, y, MAP_W - PADDING, y + NODE_H]

        if is_active:
            draw.rounded_rectangle(
                node_rect, radius=NODE_RADIUS, fill=ACTIVE_COLOR
            )
            # Truncate label to fit
            display = _truncate_label(label, draw, font_active, MAP_W - PADDING * 2 - 10)
            draw.text(
                (PADDING + 8, y + (NODE_H - 14) // 2),
                display,
                font=font_active,
                fill=ACTIVE_TEXT,
            )
        else:
            draw.rounded_rectangle(
                node_rect, radius=NODE_RADIUS,
                fill=(30, 30, 30, 140),
                outline=(70, 70, 70, 160),
                width=1,
            )
            display = _truncate_label(label, draw, font_inactive, MAP_W - PADDING * 2 - 10)
            draw.text(
                (PADDING + 8, y + (NODE_H - 13) // 2),
                display,
                font=font_inactive,
                fill=INACTIVE_TEXT,
            )

        y += NODE_H + 6

    return img


def _truncate_label(label: str, draw: ImageDraw.Draw, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    """Truncates label to fit within max_w pixels."""
    if draw.textlength(label, font=font) <= max_w:
        return label
    while label and draw.textlength(label + "…", font=font) > max_w:
        label = label[:-1]
    return label + "…"


concept_map_agent = Agent(
    name="concept_map_agent",
    model=ROUTING_MODEL,
    description=(
        "Generates per-segment concept map overlay PNGs using PIL. "
        "Each frame highlights the current topic in the mini-map shown in the video corner."
    ),
    instruction=(
        "You are the Concept Map Agent. "
        "Call the generate_concept_map_frames tool immediately — it reads data from session state automatically. "
        "No parameters needed. Return the tool's output as-is."
    ),
    tools=[generate_concept_map_frames],
)
