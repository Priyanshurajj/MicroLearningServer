# EduReelADK — Architectural Implementation Plan

## Context

EduReelADK converts educational transcripts into short-form vertical videos (1080x1920) via a multi-agent Google ADK pipeline. This plan covers 13 improvements: new agents, visual quality, data model changes, and performance optimizations. Key architectural change: split the monolithic `visual_asset_agent` into dedicated `image_agent` and `manim_code_agent`.

---

## Current Architecture (Baseline)

```
root_agent (SequentialAgent)
├── script_agent              → script_output
├── creative_director_agent   → enhanced_script
├── asset_generator (ParallelAgent)
│   ├── tts_agent             → tts_output
│   └── visual_asset_agent    → visual_output  ← monolithic: images + manim code mixed
├── manim_qc_agent            → qc_output
└── video_editor_agent        → video_output
```

---

## Target Architecture

```
root_agent (SequentialAgent)
├── storytelling_agent        [NEW] output_key="narrative_transcript"
├── hook_agent                [NEW] → state["hook_segment"]
├── script_agent              [MODIFIED] reads narrative_transcript, prepends hook_segment
├── script_review_agent       [NEW] validates JSON/LaTeX, fixes in-place → state["script_output"]
├── creative_director_agent   [MODIFIED] cinematic prompts, background_image flag, text_overlay field
├── prompt_review_agent       [NEW] checks Imagen policy, manim_spec completeness
├── asset_generator (ParallelAgent)
│   ├── tts_agent             [MODIFIED] ThreadPoolExecutor per segment → tts_output
│   ├── image_agent           [NEW from split] all Imagen calls (general + manim bg) → image_output
│   └── manim_code_agent      [NEW from split] all Manim .py generation → manim_code_output
├── manim_qc_agent            [MODIFIED] reads manim_code_output + image_output (for bg)
├── concept_map_agent         [NEW] generates per-segment PIL overlay PNGs → concept_map_output
└── video_editor_agent        [MODIFIED] reads qc_output + image_output; no Ken Burns; text overlays; concept map
```

**`visual_asset_agent.py` is replaced by `image_agent.py` + `manim_code_agent.py`.**

---

## State Flow

```
storytelling_agent  → narrative_transcript
hook_agent          → hook_segment
script_agent        → script_output
script_review_agent → script_output (corrected in-place)
creative_director   → enhanced_script
prompt_review_agent → enhanced_script (corrected in-place)

[PARALLEL]
tts_agent           → tts_output
image_agent         → image_output   ← ALL Imagen calls: general images + maths bg images
manim_code_agent    → manim_code_output ← ALL Manim .py code

manim_qc_agent      → qc_output (reads manim_code_output + image_output for bg lookup)
concept_map_agent   → concept_map_output
video_editor_agent  → video_output (reads qc_output + image_output + concept_map_output)
```

---

## Data Model Changes

Segment shape additions (all new fields optional, backward-compatible):

```json
{
  "segment_id": 2,
  "segment_type": "maths",
  "narration": "...",
  "visual_description": "...",
  "duration_seconds": 8.0,
  "math_expression": "a^2 + b^2 = c^2",
  "math_expressions": ["a^2 + b^2 = c^2", "c = \\sqrt{a^2+b^2}"],
  "is_hook": false,
  "background_image": true,
  "text_overlay": {
    "lines": ["Pythagorean Theorem"],
    "highlight_words": ["Pythagorean"]
  }
}
```

Math expressions fallback in `manim_code_agent`:
```python
math_exprs = seg.get("math_expressions") or ([seg["math_expression"]] if seg.get("math_expression") else [])
```

### `image_output` state format
```json
{
  "run_id": "abc123",
  "images": [
    {"segment_id": 1, "asset_type": "image", "image_file_path": "/output/.../images/segment_1.png", "is_background": false},
    {"segment_id": 3, "asset_type": "image", "image_file_path": "/output/.../images/segment_3_bg.png", "is_background": true}
  ]
}
```

### `manim_code_output` state format
```json
{
  "run_id": "abc123",
  "manim_assets": [
    {"segment_id": 2, "asset_type": "manim_code", "code_file_path": "...", "scene_name": "Segment2Scene"}
  ]
}
```

---

## Phase 1 — Bug Fixes & Quick Wins

### 1a. Remove Ken Burns Effect (Change 4)
**File:** [agents/video_editor_agent.py](agents/video_editor_agent.py#L197)
- Delete line 197: `clip = clip.resized(lambda t: 1 + 0.03 * t)` — this causes image content to overflow the frame edges

### 1b. Cinematic Image Prompts (Change 5)
**File:** [agents/creative_director_agent.py](agents/creative_director_agent.py)
- In `CREATIVE_ENHANCEMENT_PROMPT` for general segments, replace any "flat design / 3D render" options with:
  ```
  STRICTLY photorealistic and cinematic. Shot on RED camera. 8K ultra-detailed.
  BBC/National Geographic documentary style. Dramatic lighting (chiaroscuro or golden hour).
  No illustrations, no cartoons, no flat design, no vector art, no text overlays.
  ```

### 1c. Multiple Equations per Segment (Change 9)
**File:** [agents/script_generation_agent.py](agents/script_generation_agent.py)
- Update `SCRIPT_GENERATION_PROMPT` example JSON to show `math_expressions: ["...", "..."]` array

**File:** `agents/manim_code_agent.py` (new, from split)
- Use fallback chain for math expressions (see above)
- Update `MANIM_CODE_PROMPT` to pass the list and instruct use of `Transform()` to morph between consecutive equations

---

## Phase 2 — Split `visual_asset_agent` + New Pipeline Agents

### 2a. Split visual_asset_agent → image_agent + manim_code_agent

**New file:** `agents/image_agent.py`
- Tool `generate_images(tool_context)`:
  - Reads `enhanced_script`
  - Iterates segments using `ThreadPoolExecutor`:
    - **General segments** (`segment_type == "general"`): call Imagen 3.0, save `segment_{id}.png`, `is_background: false`
    - **Maths segments with `background_image: true`**: call Imagen 3.0 with prompt appended with `"blurred, defocused, soft bokeh, dark, atmospheric, suitable as video background"`, save `segment_{id}_bg.png`, `is_background: true`
    - **Maths segments without `background_image`**: skip
  - Writes all results to `state["image_output"]`

**New file:** `agents/manim_code_agent.py`
- Tool `generate_manim_code(tool_context)`:
  - Reads `enhanced_script`
  - For each maths segment (ThreadPoolExecutor), calls Gemini CODE_MODEL to generate Manim .py
  - Uses `math_expressions[]` (with fallback)
  - Writes to `state["manim_code_output"]`

**Delete/deprecate:** `agents/visual_asset_agent.py` — functionality fully migrated

**File:** [agents/agent.py](agents/agent.py)
- Replace `visual_asset_agent` in `asset_generator` ParallelAgent with `image_agent` and `manim_code_agent`:
  ```python
  asset_generator = ParallelAgent(
      name="asset_generator",
      sub_agents=[tts_agent, image_agent, manim_code_agent],
  )
  ```

### 2b. Storytelling Agent (Change 3)
**New file:** `agents/storytelling_agent.py`
- Use `output_key="narrative_transcript"` (no tool — saves one routing LLM call)
- Instruction: rewrite transcript into engaging narrative prose, preserving all facts

**File:** [agents/script_generation_agent.py](agents/script_generation_agent.py)
- In `generate_script()`: use `tool_context.state.get("narrative_transcript", "")` as transcript if present

### 2c. Hook Agent (Change 1)
**New file:** `agents/hook_agent.py`
- Tool `generate_hook_segment()`:
  - Calls Gemini TEXT_MODEL with transcript
  - Generates one segment: `segment_id: 0`, `segment_type: "general"`, `is_hook: true`, `duration_seconds: 6`
  - Dramatic question in narration; cinematic `image_prompt`
  - Writes to `state["hook_segment"]`

**File:** [agents/script_generation_agent.py](agents/script_generation_agent.py)
- In `generate_script()`: if `state["hook_segment"]` exists, prepend it to segments list before writing `script_output`

### 2d. Review Agents (Change 13)
**New file:** `agents/script_review_agent.py`
- Tool `review_script()`: validates `script_output` via Gemini — checks non-empty narrations, valid LaTeX in `math_expressions`, 3-8 segments, no duplicate IDs; writes corrected JSON back to `state["script_output"]`

**New file:** `agents/prompt_review_agent.py`
- Tool `review_prompts()`: validates `enhanced_script` — checks image prompts for Imagen policy violations (rewrites with safer alternatives), ensures `manim_spec` has all required fields; writes corrected JSON back to `state["enhanced_script"]`

**File:** [agents/agent.py](agents/agent.py) — full updated pipeline:
```python
root_agent = SequentialAgent(sub_agents=[
    storytelling_agent,
    hook_agent,
    script_agent,
    script_review_agent,
    creative_director_agent,
    prompt_review_agent,
    asset_generator,        # ParallelAgent: tts + image + manim_code
    manim_qc_agent,
    concept_map_agent,
    video_editor_agent,
])
```

---

## Phase 3 — Performance Optimizations

### 3a. Async Segment Processing (Change 12)
**File:** `agents/tts_agent.py`
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor(max_workers=min(len(segments), 5)) as executor:
    futures = {executor.submit(_sync_tts_segment, seg, audio_dir): seg for seg in segments}
    for future in as_completed(futures):
        audio_segments.append(future.result())
# Write to state AFTER all futures complete — not inside workers
```

**Files:** `agents/image_agent.py`, `agents/manim_code_agent.py`
- Same `ThreadPoolExecutor` pattern for all Imagen calls and Gemini code gen calls
- Each segment writes to a unique file path — no collision risk
- State write happens only after `executor` context exits

### 3b. LoopAgent Decision (Change 11)
**Decision: Keep Python for-loop in `manim_qc_agent.py`. No change needed.**

Reasoning: `LoopAgent` requires one static agent instance per iteration target. For N manim segments, you'd need N `LoopAgent` instances — impossible in ADK's static graph model. The Python for-loop has natural local variable state for attempt counts and error messages. It is the correct tool here.

### 3c. Reduce Tool-Call Overhead (Change 10)
- `storytelling_agent` uses `output_key` → eliminates one tool-routing LLM call ✓ (done in 2b)
- Other agents keep tools because they do Python I/O (file writes, JSON parsing) that `output_key` can't handle

---

## Phase 4 — Visual Feature Additions

### 4a. Background Images for Manim Compositing (Change 8)

**File:** [agents/manim_qc_agent.py](agents/manim_qc_agent.py)
- In `execute_manim_qc()`: read both `manim_code_output` AND `image_output` from state
- Build a lookup: `bg_lookup = {img["segment_id"]: img["image_file_path"] for img in image_data["images"] if img["is_background"]}`
- For each rendered manim asset, attach: `asset["background_image_path"] = bg_lookup.get(seg_id, "")`
- Write to `qc_output` with `background_image_path` per asset

**File:** [agents/video_editor_agent.py](agents/video_editor_agent.py)
- New helper `_create_manim_with_background(video_path, bg_path, duration)`:
  ```python
  from PIL import Image, ImageFilter
  pil_bg = Image.open(bg_path).resize((REEL_WIDTH, REEL_HEIGHT), Image.LANCZOS)
  pil_bg = pil_bg.filter(ImageFilter.GaussianBlur(radius=20))
  bg_array = (np.array(pil_bg) * 0.4).astype(np.uint8)   # darken to 40%
  bg_clip = ImageClip(bg_array).with_duration(duration)
  manim_clip = VideoFileClip(video_path).resized(0.90)     # 90% scale, background visible at edges
  return CompositeVideoClip([bg_clip, manim_clip.with_position("center")], size=(REEL_WIDTH, REEL_HEIGHT))
  ```
  Blur is applied once at load time (not per-frame) to avoid 30× slowdown.
- In `_create_segment_clip()`: if `asset_info.get("background_image_path")`, call this helper

### 4b. Text Overlays with Yellow Word Highlighting (Change 6)
**File:** [agents/video_editor_agent.py](agents/video_editor_agent.py)
- New helper `_render_text_overlay_pil(text_overlay, width, height, duration) -> ImageClip`:
  - Create RGBA PIL canvas (1080×1920, transparent)
  - Words in `highlight_words`: draw yellow rounded rect (rgba 255,220,0,230) behind word, then dark text
  - Other words: dark shadow (+2,+2 offset), then white text
  - Lines centered horizontally, starting at y = 72% of frame height
  - Font: `ImageFont.truetype(OVERLAY_FONT_PATH, 52)` with `load_default()` fallback
  - Return `ImageClip(np.array(rgba_img)).with_duration(duration)`
- In `_create_segment_clip()`: if `seg.get("text_overlay")`, composite this clip on top

**File:** [agents/creative_director_agent.py](agents/creative_director_agent.py)
- In `CREATIVE_ENHANCEMENT_PROMPT`: instruct model to add `text_overlay` **only when it adds value** — e.g., when a key term, formula name, or concept benefits from visual reinforcement on screen. Most conversational/narrative segments should NOT have a text overlay. Prompt guidance:
  ```
  Add "text_overlay" ONLY IF the segment introduces a named concept, formula, or key term
  that a viewer would benefit from seeing written on screen. Leave it absent for narrative
  or transitional segments. When added, include 1-2 lines maximum and only 1-3 highlight_words.
  ```

**File:** [agents/config.py](agents/config.py)
- Add `OVERLAY_FONT_PATH = os.getenv("OVERLAY_FONT_PATH", "arial.ttf")`

### 4c. TTS Quality (Change 7)
**File:** `agents/tts_agent.py`
- Replace gTTS with Google Cloud Text-to-Speech (Neural2 voices):
  ```python
  from google.cloud import texttospeech
  # Voice: "en-US-Neural2-J" (male) or "en-US-Neural2-F" (female)
  ```
- Guard with `USE_CLOUD_TTS = os.getenv("USE_CLOUD_TTS", "false").lower() == "true"` — gTTS remains as fallback
- Add `google-cloud-texttospeech` to `requirements.txt`

**File:** [agents/video_editor_agent.py](agents/video_editor_agent.py)
- Add `clip = clip.fadein(0.3).fadeout(0.3)` before appending to clips list for smooth transitions between segments

---

## Phase 5 — Advanced Visual Features

### 5a. Concept Map Overlay (Change 2)
**New file:** `agents/concept_map_agent.py`
- Tool `generate_concept_map_frames()`:
  - Reads `enhanced_script`, extracts topic label (first 4 words of narration) per segment
  - For each segment `i`, generates a 240×380 RGBA PIL image:
    - Dark semi-transparent background (rgba 0,0,0,160)
    - Vertical list of all topic labels with small connecting lines
    - Active topic `i`: yellow filled rounded rect + black text
    - Inactive topics: gray text
  - Saves `output/{run_id}/concept_map/frame_{seg_id}.png`
  - Writes `{"frames": {"0": "/path/frame_0.png", ...}}` to `state["concept_map_output"]`

**File:** [agents/agent.py](agents/agent.py)
- Insert `concept_map_agent` after `manim_qc_agent`

**File:** [agents/video_editor_agent.py](agents/video_editor_agent.py)
- In `compose_final_video()`: read `concept_map_output`
- In `_create_segment_clip()`: load frame PNG, create `ImageClip`, position at top-right with 20px margin:
  ```python
  map_clip = ImageClip(map_path).with_duration(duration)
  clip = CompositeVideoClip([clip, map_clip.with_position((REEL_WIDTH - 260, 20))])
  ```

---

## Key Decisions

| Question | Decision | Reason |
|---|---|---|
| visual_asset_agent split | **image_agent + manim_code_agent** | Single responsibility; both run in parallel; image_agent handles ALL Imagen calls including Manim backgrounds |
| Manim background images | **image_agent generates them** | Consistent — all Imagen calls in one place |
| LoopAgent for ManimQC | **Keep Python for-loop** | LoopAgent can't handle N-segment iteration with static ADK agent graph |
| Concept map rendering | **PIL only (no NetworkX)** | Deterministic, fast, no extra dep |
| Storytelling agent | **output_key, no tool** | Saves one tool-routing LLM call |
| Hook segment duration | **6 seconds** (not 30s) | 30s hook on a 60s reel is too long |
| Background blur method | **PIL GaussianBlur at load time** | Per-frame blur = 30× slower |
| Text overlay rendering | **PIL** (not MoviePy TextClip) | Avoids ImageMagick Windows dependency |
| Cloud TTS | **Optional via USE_CLOUD_TTS env** | gTTS as safe fallback |

---

## Files to Create

| File | Purpose |
|---|---|
| `agents/image_agent.py` | All Imagen API calls: general images + manim background images |
| `agents/manim_code_agent.py` | All Manim .py code generation (split from visual_asset_agent) |
| `agents/storytelling_agent.py` | Narrative wrapping (output_key agent) |
| `agents/hook_agent.py` | Curiosity hook opening segment |
| `agents/script_review_agent.py` | Script JSON validation & repair |
| `agents/prompt_review_agent.py` | Image prompt & manim_spec review |
| `agents/concept_map_agent.py` | Per-segment concept map PIL rendering |

## Files to Modify

| File | Key Changes |
|---|---|
| [agents/agent.py](agents/agent.py) | Replace visual_asset_agent with image_agent+manim_code_agent; add 5 new agents to pipeline |
| [agents/script_generation_agent.py](agents/script_generation_agent.py) | Read narrative_transcript; prepend hook_segment; math_expressions[] in prompt |
| [agents/creative_director_agent.py](agents/creative_director_agent.py) | Cinematic prompts; background_image flag; text_overlay field |
| [agents/manim_qc_agent.py](agents/manim_qc_agent.py) | Read manim_code_output + image_output; attach bg path to qc_output |
| [agents/tts_agent.py](agents/tts_agent.py) | ThreadPoolExecutor; optional Cloud TTS |
| [agents/video_editor_agent.py](agents/video_editor_agent.py) | Remove Ken Burns; Manim+bg compositing; PIL text overlay; concept map overlay; crossfades |
| [agents/config.py](agents/config.py) | Add OVERLAY_FONT_PATH, USE_CLOUD_TTS |
| `requirements.txt` | Add google-cloud-texttospeech |

## Files to Delete

| File | Reason |
|---|---|
| `agents/visual_asset_agent.py` | Fully replaced by image_agent.py + manim_code_agent.py |

---

## Verification

1. POST `/generate` with a transcript containing 2+ math equations
2. Verify `script_output` has `math_expressions: []` for maths segments
3. Verify `image_output` has both regular images and `_bg` background images for flagged maths segments
4. Verify `manim_code_output` has only maths segments
5. Verify `output/{run_id}/concept_map/` has one PNG per segment
6. Play `final_reel.mp4`:
   - No Ken Burns zoom overflow on image slides
   - Concept map visible in top-right corner with active node highlighted
   - Text overlays with yellow-background word highlights
   - Cinematic photorealistic images (no cartoons)
   - Manim clips with blurred background images where applicable
   - Smooth fade transitions between segments
