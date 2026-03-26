import json
from google.adk.agents import Agent


def run_manim_qc(visual_output_json: str) -> dict:
    """
    Quality-checks and 'executes' Manim code for maths segments.
    In production: runs each Manim script in a sandbox, catches errors,
    auto-patches the code, and retries. Returns rendered .mp4 paths.
    Dummy implementation: marks all Manim segments as successfully rendered.
    """
    try:
        visual_data = json.loads(visual_output_json)
    except json.JSONDecodeError:
        return {"status": "error", "error_message": "Invalid JSON provided to Manim QC agent."}

    assets = visual_data.get("visual_assets", [])
    qc_results = []

    for asset in assets:
        if asset.get("asset_type") == "manim_code":
            seg_id = asset["segment_id"]
            qc_results.append({
                "segment_id": seg_id,
                "asset_type": "manim_video",
                "manim_code": asset.get("manim_code", ""),
                "render_status": "success",
                "render_attempts": 1,
                "video_path": f"/tmp/manim/segment_{seg_id}.mp4",
                "duration_seconds": 5.0,
                "resolution": "1080x1920",
            })
        else:
            qc_results.append(asset)

    result = {
        "qc_assets": qc_results,
        "manim_rendered": sum(1 for r in qc_results if r.get("asset_type") == "manim_video"),
        "images_passed_through": sum(1 for r in qc_results if r.get("asset_type") == "image"),
        "total_assets": len(qc_results),
    }

    return {"status": "success", "qc_output": json.dumps(result)}


manim_qc_agent = Agent(
    name="manim_qc_agent",
    model="gemini-3-flash-preview",
    description=(
        "Quality-checks generated Manim Python code, executes it in a sandbox, "
        "auto-heals errors, and returns rendered .mp4 clip paths. "
        "Passes through image assets unchanged."
    ),
    instruction=(
        "You are the Manim QC Agent. You receive visual assets from 'visual_output' "
        "in the session state. Use the run_manim_qc tool, passing the visual output JSON. "
        "Return ONLY the raw JSON string from the tool's 'qc_output' field. "
        "Do not add any extra commentary."
    ),
    tools=[run_manim_qc],
    output_key="qc_output",
)
