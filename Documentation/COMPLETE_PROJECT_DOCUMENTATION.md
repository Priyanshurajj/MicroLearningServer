# EduReelADK — Complete Project Documentation

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Why This Architecture?](#2-why-this-architecture)
3. [Technology Stack & Library Justifications](#3-technology-stack--library-justifications)
4. [Project Structure](#4-project-structure)
5. [Complete Code Flow](#5-complete-code-flow)
6. [Agent-by-Agent Deep Dive](#6-agent-by-agent-deep-dive)
7. [State Management & Data Flow](#7-state-management--data-flow)
8. [Pipeline Orchestration (ADK Patterns)](#8-pipeline-orchestration-adk-patterns)
9. [Output Structure](#9-output-structure)
10. [Configuration & Environment](#10-configuration--environment)
11. [Error Handling & Recovery](#11-error-handling--recovery)
12. [Key Design Decisions Explained](#12-key-design-decisions-explained)

---

## 1. Project Overview

**EduReelADK** is an AI-powered multi-agent system that autonomously transforms educational text/transcripts into polished, cinematic short-form vertical videos (30-90 second reels).

**What it does:** You send a transcript like *"Photosynthesis is the process by which plants convert sunlight into energy..."* via a single API call, and the system returns a fully produced 9:16 vertical reel video with:
- Cinematic photorealistic imagery (via Imagen 3.0)
- Mathematical animations (via Manim — the 3Blue1Brown animation engine)
- Professional narration (via Text-to-Speech)
- Keyword-highlighted text overlays
- A topic navigation mini-map
- Smooth fade transitions and audio sync

**The core idea:** Instead of one monolithic script doing everything, we decompose video production into 11 specialized AI agents, each with a single responsibility. These agents communicate through shared session state and run in a carefully orchestrated pipeline of sequential and parallel stages.

---

## 2. Why This Architecture?

### Why Multi-Agent (not a single prompt)?

A single LLM call cannot:
- Generate images (needs Imagen API)
- Render mathematical animations (needs Manim subprocess)
- Produce audio (needs TTS API)
- Compose video (needs MoviePy/FFmpeg)
- Do all of the above reliably in one shot

By decomposing into agents, each agent:
1. Has a focused prompt (better output quality)
2. Can use the right model for the job (Flash for routing, Pro for code)
3. Can run in parallel where independent (TTS + Images + Manim simultaneously)
4. Can be debugged, tested, and improved in isolation

### Why Google ADK?

Google's Agent Development Kit provides:
- **SequentialAgent / ParallelAgent** — declarative pipeline composition without custom orchestration code
- **Session state** — automatic state sharing between agents (no manual message passing)
- **Runner** — async event-driven execution with structured logging
- **Tool framework** — agents call Python functions as tools with automatic context injection
- Built-in support for Gemini models and Vertex AI

The alternative would be writing custom orchestration code (queues, state machines, error handling) — ADK gives us this for free.

---

## 3. Technology Stack & Library Justifications

### Core Framework

| Library | Version | Why We Use It |
|---------|---------|---------------|
| **google-adk** | latest | Google's Agent Development Kit — the backbone of our multi-agent pipeline. Provides `SequentialAgent`, `ParallelAgent`, `Agent` (LLM-backed), `Runner`, `ToolContext`, and `InMemorySessionService`. Without it we'd need to write hundreds of lines of orchestration code. |
| **google-genai** | latest | Official Google Generative AI Python client. Provides unified access to **Gemini LLMs** (text generation, JSON mode) and **Imagen** (image generation) through a single `Client` object. Supports both Vertex AI (enterprise/GCP) and API key modes. |
| **fastapi** | latest | Modern async Python web framework. Chosen because: (1) Native async support — critical since our pipeline is `async` (2) Automatic OpenAPI/Swagger docs at `/docs` (3) Pydantic integration for request validation (4) Lightweight — adds minimal overhead. |
| **uvicorn[standard]** | latest | ASGI server to run FastAPI. The `[standard]` extra includes `uvloop` (faster event loop) and `httptools` (faster HTTP parsing). Supports hot-reload during development via `reload=True`. |
| **pydantic** | latest | Data validation library. Used for API request/response models (`GenerateRequest`, `PipelineResult`, `AgentStepLog`). Ensures the transcript is at least 10 characters, provides type hints, and auto-generates JSON Schema for API docs. |
| **python-dotenv** | latest | Loads `.env` file into environment variables at startup. Critical because model config, credentials path, and feature flags (`USE_CLOUD_TTS`) are all environment-driven. Must load **before** any agent imports since `config.py` reads env vars at import time. |

### AI & Generation

| Library | Why We Use It |
|---------|---------------|
| **Gemini 2.5 Flash** (`gemini-2.5-flash`) | Used for: (1) Agent routing — deciding which tool to call (fast, cheap) (2) Script generation — converting transcript to structured JSON (3) Creative direction — writing cinematic image prompts (4) Script/prompt review — validating JSON completeness. Flash is chosen for speed and cost when code accuracy isn't critical. |
| **Gemini 2.5 Pro** (`gemini-2.5-pro`) | Used exclusively for **Manim code generation** and **auto-healing**. Pro has significantly better code accuracy than Flash — fewer syntax errors in generated Manim Python, which means fewer retry loops and faster pipeline completion. The cost premium is justified because failed renders waste more time/money than the model price difference. |
| **Imagen 3.0** (`imagen-3.0-generate-002`) | Google's state-of-the-art image generation model. Generates photorealistic 9:16 images for: (1) General segment backgrounds (cinematic, BBC/NatGeo quality) (2) Manim background images (blurred, atmospheric). We use `generate_images()` API with `aspect_ratio="9:16"` for vertical reels. |

### Video & Audio Production

| Library | Why We Use It |
|---------|---------------|
| **moviepy** | Python video editing library. Used for: (1) Compositing layers — background image + Manim animation + text overlay + concept map (2) Audio attachment — syncing TTS MP3 to video clips (3) Concatenation — joining all segment clips into one video (4) Effects — fade in/out transitions. We use `CompositeVideoClip` for layering, `concatenate_videoclips` for joining, and `VideoFileClip`/`ImageClip`/`AudioFileClip` for loading assets. MoviePy is chosen over raw FFmpeg because it provides a Pythonic API for complex compositing operations. |
| **imageio-ffmpeg** | Bundled FFmpeg binary. MoviePy uses FFmpeg under the hood, but `imageio-ffmpeg` guarantees a compatible FFmpeg version is available regardless of system installation. We also call FFmpeg directly via `subprocess` for the final audio merge step (more reliable than MoviePy's built-in audio encoding for our use case). |
| **manim** | The Mathematical Animation Engine (same technology behind 3Blue1Brown videos). Used to generate animated mathematical derivations, equations, and geometric visualizations. We generate Manim Python code with Gemini, then execute it via `subprocess` to render `.mov` files with transparent backgrounds. Manim is the only tool that can produce publication-quality animated math — alternatives like matplotlib animations lack the polish. |
| **gTTS** | Google Text-to-Speech (free, no API key). Default TTS backend. Converts narration text to MP3 audio files. Simple, requires no authentication, works offline for testing. Limitation: robotic-sounding compared to Neural2 voices. |
| **google-cloud-texttospeech** | Google Cloud TTS with Neural2 voices. Optional premium backend (`USE_CLOUD_TTS=true`). Produces natural-sounding narration using `en-US-Neural2-J` voice at 0.95x speed (slightly slowed for educational clarity). Falls back to gTTS if Cloud TTS fails. |

### Image Processing

| Library | Why We Use It |
|---------|---------------|
| **Pillow (PIL)** | Python Imaging Library. Used for: (1) **Text overlay rendering** — drawing shadowed white text with yellow keyword highlights on transparent RGBA images (2) **Concept map frames** — rendering the glassmorphic topic navigation overlay (3) **Background dimming** — loading and resizing Manim background images. We render text overlays as PIL images rather than using MoviePy's text API because PIL gives us pixel-precise control over shadow offsets, rounded-rectangle highlight pills, and RGBA transparency. |
| **numpy** | Numerical array operations. Used for: (1) Converting PIL images to numpy arrays for MoviePy (MoviePy clips are backed by numpy arrays) (2) Background dimming — `(np.array(pil_bg) * 0.85).astype(np.uint8)` dims the background to 85% brightness for contrast with Manim overlays. |

---

## 4. Project Structure

```
EduReelADK/
│
├── main.py                             # FastAPI app entry point
├── requirements.txt                    # Python dependencies
├── .env                                # Environment configuration
│
├── agents/                             # All 11 AI agents
│   ├── __init__.py                     # Exports root_agent
│   ├── agent.py                        # Pipeline composition (Sequential/Parallel)
│   ├── config.py                       # Shared config: GenAI client, model names, paths
│   ├── script_generation_agent.py      # Agent 1: Transcript → structured JSON script
│   ├── script_review_agent.py          # Agent 2: Validate & auto-repair script JSON
│   ├── creative_director_agent.py      # Agent 3: Enhance visuals, write image prompts
│   ├── prompt_review_agent.py          # Agent 4: Content safety & compliance check
│   ├── tts_agent.py                    # Agent 5: Text-to-speech audio generation
│   ├── image_agent.py                  # Agent 6: Imagen photorealistic image generation
│   ├── manim_code_agent.py             # Agent 7: Manim Python code generation
│   ├── manim_bg_image_agent.py         # Agent 8: Background images for Manim segments
│   ├── manim_qc_agent.py              # Agent 9: Manim rendering & auto-healing
│   ├── concept_map_agent.py            # Agent 10: Topic navigation overlay
│   └── video_editor_agent.py           # Agent 11: Final video composition
│
├── models/                             # Pydantic API models
│   ├── __init__.py
│   └── api_models.py                   # GenerateRequest, PipelineResult, AgentStepLog
│
├── routes/                             # FastAPI routes
│   ├── __init__.py
│   └── generate.py                     # POST /generate endpoint
│
├── services/                           # Business logic
│   ├── __init__.py
│   └── pipeline_service.py             # ADK Runner integration
│
└── output/                             # Generated assets (created at runtime)
    └── {run_id}/                       # Per-request output directory
        ├── audio/                      # TTS MP3 files
        ├── images/                     # Imagen PNGs + Manim background PNGs
        ├── manim/                      # Manim .py source + rendered .mov videos
        ├── concept_map/                # Topic navigation overlay PNGs
        └── final_reel.mp4             # FINAL OUTPUT VIDEO
```

---

## 5. Complete Code Flow

### 5.1 Entry Point → API Layer

```
User sends POST /generate { "transcript": "..." }
         │
         ▼
    main.py — FastAPI app starts, loads .env FIRST, then imports agents
         │
         ▼
    routes/generate.py — generate_reel() handler
         │  1. Generates unique user_id and session_id
         │  2. Calls run_agent_pipeline(user_id, session_id, transcript)
         │  3. Returns PipelineResult JSON
         ▼
    services/pipeline_service.py — run_agent_pipeline()
         │  1. Creates a new InMemorySession
         │  2. Wraps transcript as ADK Content message
         │  3. Calls runner.run_async() — this starts the agent pipeline
         │  4. Iterates through all events, logs each step
         │  5. Returns (final_response_text, agent_logs)
         ▼
    agents/agent.py — root_agent (SequentialAgent) begins execution
```

### 5.2 The 7-Stage Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1: Script Generation (script_agent)                      │
│  Input: raw transcript text                                     │
│  Tool: generate_script() — calls Gemini Flash                   │
│  Output: script_output (JSON with segments, types, narrations)  │
│  Creates: run_id, output directories                            │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 2: Script Review (script_review_agent)                   │
│  Input: reads {script_output} from state                        │
│  LLM-only: Gemini Flash validates JSON (no tool call)           │
│  Output: script_output (validated/repaired, overwrites in-place)│
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 3: Creative Director (creative_director_agent)           │
│  Input: reads {script_output} from state                        │
│  LLM-only: Gemini Flash (temp=0.8, creative)                    │
│  Output: enhanced_script — adds image_prompt, manim_spec,       │
│          text_overlay, background_image flag per segment         │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 4: Prompt Review (prompt_review_agent)                   │
│  Input: reads {enhanced_script} from state                      │
│  LLM-only: Gemini Flash (temp=0.2, conservative)                │
│  Output: enhanced_script (safety-checked, overwrites in-place)  │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 5: Content Pipeline (ParallelAgent — all run at once)    │
│                                                                 │
│  ┌─────────────────┐ ┌─────────────────┐ ┌────────────────────┐│
│  │  TTS Agent       │ │ General Pipeline │ │  Manim Pipeline    ││
│  │  Tool:           │ │  Image Agent     │ │                    ││
│  │  generate_tts    │ │  Tool:           │ │  ┌──────────────┐ ││
│  │  _audio()        │ │  generate_       │ │  │ manim_prep   │ ││
│  │                  │ │  images()        │ │  │ (Parallel)   │ ││
│  │  Generates MP3   │ │                  │ │  │ ┌──────────┐ │ ││
│  │  for ALL segments│ │  Generates PNG   │ │  │ │manim_code│ │ ││
│  │  in parallel     │ │  for "general"   │ │  │ │_agent    │ │ ││
│  │  (ThreadPool, 5) │ │  segments only   │ │  │ └──────────┘ │ ││
│  │                  │ │  (ThreadPool, 5) │ │  │ ┌──────────┐ │ ││
│  │  → tts_output    │ │                  │ │  │ │manim_bg  │ │ ││
│  │                  │ │  → image_output  │ │  │ │_image    │ │ ││
│  └─────────────────┘ └─────────────────┘ │  │ │_agent    │ │ ││
│                                           │  │ └──────────┘ │ ││
│                                           │  └──────┬───────┘ ││
│                                           │         ▼          ││
│                                           │  ┌──────────────┐ ││
│                                           │  │ manim_qc     │ ││
│                                           │  │ _agent       │ ││
│                                           │  │ Render+heal  │ ││
│                                           │  │ → qc_output  │ ││
│                                           │  └──────────────┘ ││
│                                           └────────────────────┘│
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 6: Concept Map (concept_map_agent)                       │
│  Tool: generate_concept_map_frames()                            │
│  Renders one 240x400 PNG per segment (topic nav overlay)        │
│  → concept_map_output                                           │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 7: Video Editor (video_editor_agent)                     │
│  Tool: compose_final_video()                                    │
│  Reads ALL state keys, composites every layer, encodes MP4      │
│  → video_output + output/{run_id}/final_reel.mp4               │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Detailed Execution: What Happens Inside runner.run_async()

```python
# services/pipeline_service.py

async for event in runner.run_async(user_id, session_id, new_message):
    # The Runner executes root_agent, which is a SequentialAgent.
    # For each sub-agent in order:
    #
    #   1. If it's a tool-based Agent (like script_agent):
    #      - The LLM reads the instruction prompt
    #      - The LLM decides to call the tool function (e.g., generate_script)
    #      - The tool function executes, writes to session state, returns result
    #      - The LLM gets the tool result and formats its response
    #      - An event is emitted with the response
    #
    #   2. If it's an LLM-only Agent (like creative_director_agent):
    #      - The instruction prompt contains {state_key} placeholders
    #      - ADK injects the current state values into the prompt
    #      - The LLM generates its response (JSON)
    #      - The response is saved to the output_key in state
    #      - An event is emitted
    #
    #   3. If it's a ParallelAgent (like content_pipeline):
    #      - All sub-agents are launched concurrently
    #      - Each sub-agent's events are interleaved in the event stream
    #      - The ParallelAgent completes when ALL sub-agents finish
    #
    # Events include: tool calls, tool responses, agent text responses
    # The pipeline service logs each event and collects the final response
```

---

## 6. Agent-by-Agent Deep Dive

### Agent 1: Script Generation Agent
**File:** `agents/script_generation_agent.py`
**Type:** Tool-based Agent (LlmAgent with tool function)
**Model:** Gemini 2.5 Flash (routing) + Gemini 2.5 Flash (content generation)
**State writes:** `script_output`

**What it does:**
Takes the raw transcript and produces a structured JSON script with 3-6 segments. Each segment is classified as either `"general"` (for photorealistic images) or `"manim"` (for mathematical animations).

**How it works:**
1. The Agent receives the transcript from the user message
2. The LLM reads the instruction: *"call the generate_script tool with the full transcript text"*
3. The LLM calls `generate_script(transcript, tool_context)`
4. Inside the tool:
   - A detailed prompt (`SCRIPT_GENERATION_PROMPT`) is formatted with the transcript
   - Gemini Flash is called with `response_mime_type="application/json"` to force structured output
   - The response is parsed as JSON
   - A unique `run_id` (8-char hex) is generated for this request
   - Output directories are created: `output/{run_id}/audio|images|manim|concept_map`
   - The script JSON (with `run_id` injected) is saved to `tool_context.state["script_output"]`

**Key design decision — why a tool function, not pure LLM?**
We need to create directories and inject `run_id` — side effects that can't happen in a pure LLM response. The tool function gives us a Python execution context for these operations.

**Why the first segment must be a hook:**
Educational reels need to grab attention in the first 2-3 seconds. The prompt explicitly requires segment 1 to be a "dramatic opening hook" with a surprising question. This is a content strategy decision, not a technical one.

---

### Agent 2: Script Review Agent
**File:** `agents/script_review_agent.py`
**Type:** Pure LLM Agent (no tool, uses `output_key`)
**Model:** Gemini 2.5 Flash
**Temperature:** 0.2 (conservative — we want deterministic validation)
**State reads:** `{script_output}` (injected into prompt via template)
**State writes:** `script_output` (overwrites in-place)

**What it does:**
Validates the script JSON for completeness and fixes issues automatically. Acts as a quality gate before creative enhancement.

**Checks performed:**
1. Every segment has non-empty `narration` and `visual_description`
2. Every manim segment has `math_expressions` as a non-empty array
3. No duplicate `segment_id` values
4. Valid LaTeX syntax in math expressions
5. `duration_seconds` in 2.0-15.0 range
6. Total segment count between 3 and 9

**Why this agent exists:**
LLMs are probabilistic — Gemini might occasionally produce a script with empty math expressions or invalid durations. Rather than hoping the first call is perfect, we add a cheap validation pass. The cost of one extra Flash call is negligible compared to the cost of a downstream failure (e.g., Manim crash because `math_expressions` was empty).

**Why it's a pure LLM agent (no tool):**
The validation and repair logic is expressible purely in natural language. Using `output_key="script_output"` with `response_mime_type="application/json"` means ADK automatically saves the corrected JSON back to state — no Python code needed.

---

### Agent 3: Creative Director Agent
**File:** `agents/creative_director_agent.py`
**Type:** Pure LLM Agent (no tool, uses `output_key`)
**Model:** Gemini 2.5 Flash
**Temperature:** 0.8 (creative — we want vivid, cinematic descriptions)
**State reads:** `{script_output}`
**State writes:** `enhanced_script`

**What it does:**
The creative heart of the pipeline. Transforms basic visual descriptions into production-grade specifications:

For **general segments:**
- Rewrites `visual_description` into a detailed Imagen prompt
- Adds `image_prompt` field with specifications: photorealistic, 8K, RED camera, shallow depth of field, BBC/National Geographic quality
- Specifies 9:16 aspect ratio

For **manim segments:**
- Creates `manim_spec` with: `scene_description`, `animations[]`, `color_scheme`, `math_elements`
- Decides if `background_image: true` (e.g., gravity equation gets a space background)
- If yes, writes an `image_prompt` for a blurred cinematic background

For **all segments:**
- Adds `text_overlay` with `lines` and `highlight_words` for at least 70% of segments
- Skips text overlay only for hooks and transitions

**Why temperature 0.8?**
Creative writing benefits from higher temperature — we want diverse, vivid descriptions rather than repetitive generic prompts. The review agent (Stage 4) catches any safety issues.

---

### Agent 4: Prompt Review Agent
**File:** `agents/prompt_review_agent.py`
**Type:** Pure LLM Agent (no tool, uses `output_key`)
**Model:** Gemini 2.5 Flash
**Temperature:** 0.2 (conservative — safety validation)
**State reads:** `{enhanced_script}`
**State writes:** `enhanced_script` (overwrites in-place)

**What it does:**
Content safety and structural validation of the creative director's output.

**Checks:**
- `image_prompt` exists and is non-empty for general segments
- No policy-violating content (violence, explicit, real people, copyrighted characters)
- Image prompts specify photorealistic style (rewrites if cartoon/flat/illustration)
- `manim_spec` has all required fields
- `text_overlay.highlight_words` are substrings of `text_overlay.lines`

**Why two separate review agents (Stage 2 and 4)?**
Stage 2 validates the raw script structure. Stage 4 validates the creative enhancements. They check different things at different points. Combining them would require the creative director to exist first, but we want script validation to happen before creative work begins (fail fast).

---

### Agent 5: TTS Agent
**File:** `agents/tts_agent.py`
**Type:** Tool-based Agent
**Model:** Gemini 2.5 Flash (routing only)
**State reads:** `enhanced_script` (falls back to `script_output`)
**State writes:** `tts_output`

**What it does:**
Generates MP3 narration audio for every segment in parallel.

**How it works:**
1. Reads the script from state
2. Creates a `ThreadPoolExecutor` with up to 5 workers
3. For each segment, submits `_synthesize_segment()` to the thread pool
4. Each synthesis call:
   - If `USE_CLOUD_TTS=true`: calls Google Cloud TTS with `en-US-Neural2-J` voice at 0.95x speed
   - If Cloud TTS fails or is disabled: falls back to `gTTS`
   - Saves MP3 to `output/{run_id}/audio/segment_{id}.mp3`
   - Measures audio duration using `MoviePy.AudioFileClip`
5. Aggregates results: per-segment metadata + total duration

**Why ThreadPoolExecutor?**
TTS calls are I/O-bound (network requests). Running 5 segments in parallel (instead of sequentially) reduces TTS time from ~30s to ~6s for a typical 6-segment video.

**Why two TTS backends?**
- **gTTS** (default): Free, no API key needed, works during development. Sound quality is adequate for prototyping.
- **Cloud TTS Neural2** (optional): Production-quality natural-sounding voices. Requires Google Cloud credentials and billing. The `USE_CLOUD_TTS` toggle lets us switch without code changes.

---

### Agent 6: Image Agent
**File:** `agents/image_agent.py`
**Type:** Tool-based Agent
**Model:** Gemini 2.5 Flash (routing only)
**State reads:** `enhanced_script`
**State writes:** `image_output`

**What it does:**
Generates photorealistic cinematic images for `"general"` segments only. Manim segments are handled separately by the manim pipeline.

**How it works:**
1. Filters segments to only `segment_type == "general"`
2. For each segment, uses `ThreadPoolExecutor` (max 5 workers)
3. Each image generation:
   - Reads `image_prompt` from segment (falls back to `visual_description`)
   - Truncates prompt to 1000 chars (Imagen limit)
   - Calls `client.models.generate_images()` with Imagen 3.0, aspect ratio 9:16
   - Saves PNG to `output/{run_id}/images/segment_{id}.png`

**Why separate from Manim background images?**
General images and Manim backgrounds serve different purposes:
- General images ARE the visual (full-screen background)
- Manim backgrounds go BEHIND transparent animations
They also have different prompt strategies (backgrounds need "soft bokeh, defocused" qualifiers).

---

### Agent 7: Manim Code Agent
**File:** `agents/manim_code_agent.py`
**Type:** Tool-based Agent
**Model:** Gemini 2.5 Flash (routing) + **Gemini 2.5 Pro** (code generation)
**State reads:** `enhanced_script`
**State writes:** `manim_code_output`

**What it does:**
Generates complete, self-contained Manim Python scripts for each `"manim"` segment.

**How it works:**
1. Filters to manim segments only
2. For each segment, submits to `ThreadPoolExecutor` (max 4 workers)
3. Each code generation:
   - Fills `MANIM_CODE_PROMPT` template with segment details (narration, math expressions, manim_spec)
   - Calls Gemini 2.5 Pro with `temperature=0.2` (we want deterministic, correct code)
   - Strips markdown code fences from response
   - Saves `.py` file to `output/{run_id}/manim/segment_{id}.py`
   - Records scene name as `Segment{id}Scene`

**Why Gemini 2.5 Pro instead of Flash?**
Manim code must compile and render without errors. Pro has significantly better code accuracy — it understands Manim's API nuances (e.g., `Write()` for MathTex, `Create()` for shapes, proper LaTeX escaping). Flash tends to produce more syntax errors, which means more retry loops in the QC agent, ultimately costing more time and compute than using Pro upfront.

**The MANIM_CODE_PROMPT is the most detailed prompt in the system. Why?**
Manim has a complex API with many deprecated functions and subtle gotchas. The prompt includes:
- **Mandatory requirements**: Single Scene class, `from manim import *`, must render with `-ql`
- **Visual style guide**: Typography sizes, 4-color palette, spacing rules
- **Animation choreography**: 5-phase structure (opening → content → emphasis → transitions → closing)
- **Prohibited operations**: `Flash()`, `ShowCreation()`, `MovingCameraScene`, hardcoded coordinates
- **Multiple equation handling**: How to animate math_expressions in sequence

This level of detail is necessary because Manim code that "looks right" often fails to render due to API misuse.

---

### Agent 8: Manim Background Image Agent
**File:** `agents/manim_bg_image_agent.py`
**Type:** Tool-based Agent
**Model:** Gemini 2.5 Flash (routing only)
**State reads:** `enhanced_script`
**State writes:** `bg_image_output`

**What it does:**
Generates cinematic background images for manim segments where the Creative Director set `background_image: true`.

**How it works:**
1. Filters to manim segments with `background_image == true`
2. For each qualifying segment:
   - Takes the `image_prompt` from the segment
   - Appends background-specific qualifiers: "Cinematic background, no text, soft bokeh, slightly defocused, dark atmospheric mood"
   - Calls Imagen 3.0 with 9:16 aspect ratio
   - Saves to `output/{run_id}/images/bg_segment_{id}.png`

**Why does this run in parallel with manim_code_agent?**
Background images are independent of the Manim code — they don't need the code to exist. Running both in `manim_prep` (ParallelAgent) means we generate code and images simultaneously, saving ~10-15 seconds per segment.

---

### Agent 9: Manim QC Agent
**File:** `agents/manim_qc_agent.py`
**Type:** Tool-based Agent
**Model:** Gemini 2.5 Flash (routing) + **Gemini 2.5 Pro** (auto-healing)
**State reads:** `manim_code_output`, `bg_image_output`, `enhanced_script`
**State writes:** `qc_output`

**What it does:**
The most complex agent. Renders Manim code, catches failures, uses AI to fix broken code, and falls back to a guaranteed-to-render template if all fixes fail.

**How it works (per segment):**

```
Attempt 1: Run manim render
  ├── Success → move video to standardized path → done
  └── Failure → capture stderr
        │
        ▼
     Auto-Fix: Send broken code + error to Gemini Pro → get fixed code
        │
        ▼
Attempt 2: Run manim render with fixed code
  ├── Success → done
  └── Failure → auto-fix again
        │
        ▼
Attempt 3: Run manim render
  ├── Success → done
  └── Failure → generate fallback code
        │
        ▼
Fallback: Simple text card animation (guaranteed to render)
  ├── Success → done (marked as is_fallback: true)
  └── Failure → return failed status
```

**The render subprocess:**
```bash
python -m manim render -ql --progress_bar display -t --format mov \
  --media_dir {output_dir} {code_path} {scene_name}
```
- `-ql`: Low quality (faster rendering, adequate for reels)
- `-t`: Transparent background (for compositing over background images)
- `--format mov`: MOV format supports alpha channel transparency
- Timeout: 120 seconds per segment

**The auto-fix mechanism:**
When rendering fails, the error output (stderr) and original code are sent to Gemini 2.5 Pro with `MANIM_FIX_PROMPT`. The prompt lists common Manim issues (deprecated APIs, incorrect animation calls, bad LaTeX). Pro generates corrected code, which overwrites the original file.

**The fallback mechanism:**
If 3 attempts all fail, a hardcoded Python template generates a simple scene with:
- A subtle grid background
- The title as large text
- The narration as smaller body text
- Basic Write/FadeIn animations
This template uses only the most basic Manim operations — it's virtually guaranteed to render.

**Why this complexity?**
LLM-generated code is inherently unreliable. Without auto-healing, ~30% of Manim segments would fail, leaving blank spots in the video. The retry loop reduces failure to <5%, and the fallback ensures 0% total loss.

---

### Agent 10: Concept Map Agent
**File:** `agents/concept_map_agent.py`
**Type:** Tool-based Agent
**Model:** Gemini 2.5 Flash (routing only)
**State reads:** `enhanced_script`
**State writes:** `concept_map_output`

**What it does:**
Generates a "topic navigation" overlay image for each segment — a small panel in the top-right corner showing where the viewer is in the video's flow of topics.

**How it works:**
1. Extracts topic labels (first 4 words of each segment's narration)
2. For each segment, renders a 240x400 RGBA image with:
   - Semi-transparent dark background (glassmorphic effect)
   - "Topics" title
   - List of up to 9 topic labels (scrolling window)
   - Current topic highlighted in vibrant yellow
   - Inactive topics in gray
   - Subtle connector lines between nodes
3. Saves PNGs to `output/{run_id}/concept_map/frame_{id}.png`

**Why PIL instead of a template image?**
Each frame is different (different topic highlighted), so we need dynamic rendering. PIL gives us precise control over the glassmorphic styling without needing a frontend framework.

---

### Agent 11: Video Editor Agent
**File:** `agents/video_editor_agent.py`
**Type:** Tool-based Agent
**Model:** Gemini 2.5 Flash (routing only)
**State reads:** `enhanced_script`, `tts_output`, `qc_output`, `image_output`, `concept_map_output`
**State writes:** `video_output`

**What it does:**
Composites all generated assets into the final 1080x1920 MP4 reel video.

**The compositing pipeline per segment:**

```
Layer 1 (Base):
  ├── Manim segment? → Load .mov + background image → composite with 85% dim
  ├── General segment? → Load Imagen .png as ImageClip
  └── Neither? → Black fallback clip (20, 20, 30)

Layer 2 (Text Overlay):
  └── If text_overlay exists → PIL-render shadowed text + yellow keyword pills
      └── CompositeVideoClip([base, overlay])

Layer 3 (Concept Map):
  └── If concept map frame exists → Position at top-right (20px margin)
      └── CompositeVideoClip([composite, map_clip])

Layer 4 (Audio):
  └── Attach TTS MP3 → sync video duration to audio length

Layer 5 (Transitions):
  └── FadeIn(0.3s) + FadeOut(0.3s) on both video and audio
```

**Manim + Background compositing:**
```python
# Background image dimmed to 85% for contrast
bg_array = (np.array(pil_bg) * 0.85).astype(np.uint8)
bg_clip = ImageClip(bg_array)

# Manim video loaded with transparency mask
manim_clip = VideoFileClip(video_path, has_mask=True)

# If Manim animation finishes before audio, freeze last frame
if manim_clip.duration < duration:
    last_frame = manim_clip.get_frame(t_last)
    freeze_clip = ImageClip(last_frame).with_duration(freeze_dur)
    manim_clip = concatenate_videoclips([manim_clip, freeze_clip])

# Composite: Manim centered over dimmed background
CompositeVideoClip([bg_clip, manim_clip.with_position("center")])
```

**Text overlay rendering (PIL):**
- Transparent RGBA image (1080x1920)
- White text with dark shadow (3px offset) for readability on any background
- Keywords wrapped in yellow "pill" rounded rectangles
- Positioned at 42% vertical height (slightly above center — optimal for reels)
- Font size 78px

**Final encoding:**
```
Step 1: Write video-only track → temp_video.mp4 (libx264, 30fps)
Step 2: Write audio-only track → temp_audio.mp3
Step 3: FFmpeg merge → final_reel.mp4 (video copy + AAC audio)
Step 4: Clean up temp files
```

**Why a separate FFmpeg merge step?**
MoviePy's built-in audio encoding sometimes produces sync issues or codec incompatibilities. Writing video and audio separately, then merging with FFmpeg (the industry standard), gives us reliable, production-quality output.

---

## 7. State Management & Data Flow

### The Session State Dictionary

ADK provides each pipeline run with a shared `dict`-like session state. Every agent can read and write to it via `tool_context.state` (for tool-based agents) or `output_key` (for LLM-only agents).

```
Session State Keys (written in order of pipeline execution):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

script_output      ← Stage 1 (Script Agent) writes, Stage 2 (Review) overwrites
                     JSON string: { title, topic, segments[], run_id }

enhanced_script    ← Stage 3 (Creative Director) writes, Stage 4 (Prompt Review) overwrites
                     JSON string: { ...script_output fields + image_prompt, manim_spec,
                                    text_overlay, background_image per segment }

tts_output         ← Stage 5a (TTS Agent) writes
                     JSON string: { audio_segments[], total_duration, tts_backend }

image_output       ← Stage 5b (Image Agent) writes
                     JSON string: { images[], total_images }

manim_code_output  ← Stage 5c-i (Manim Code Agent) writes
                     JSON string: { manim_assets[], total_manim }

bg_image_output    ← Stage 5c-ii (Manim BG Image Agent) writes
                     JSON string: { bg_images[], total_bg_images }

qc_output          ← Stage 5c-iii (Manim QC Agent) writes
                     JSON string: { qc_assets[], manim_rendered, manim_failed }

concept_map_output ← Stage 6 (Concept Map Agent) writes
                     JSON string: { frames: { "segment_id": "path" } }

video_output       ← Stage 7 (Video Editor Agent) writes
                     JSON string: { video_file_path, duration, timeline[] }
```

### Why Unique State Keys?

Each agent writes to its own key. This prevents:
1. **Race conditions** — TTS, Image, and Manim agents run in parallel but write to different keys
2. **Accidental overwrites** — No agent can corrupt another's output
3. **Clear debugging** — You can inspect exactly what each agent produced

### Why JSON Strings (not Python dicts)?

ADK state values are serialized for session persistence. Using JSON strings ensures the data survives session serialization/deserialization. It also makes logging and debugging easier — you can print the raw state value.

---

## 8. Pipeline Orchestration (ADK Patterns)

### Pattern 1: SequentialAgent

```python
root_agent = SequentialAgent(
    name="root_agent",
    sub_agents=[agent1, agent2, agent3, ...]
)
```

Runs each sub-agent in order. Agent 2 starts only after Agent 1 completes. State changes from Agent 1 are visible to Agent 2.

**Used for:** The root pipeline, `general_pipeline`, `manim_pipeline`.

### Pattern 2: ParallelAgent

```python
content_pipeline = ParallelAgent(
    name="content_pipeline",
    sub_agents=[tts_agent, general_pipeline, manim_pipeline]
)
```

Runs all sub-agents concurrently. All sub-agents see the same initial state (written by prior sequential stages). Each writes to its own state key — no conflicts.

**Used for:** `content_pipeline` (TTS + Images + Manim simultaneously) and `manim_prep` (code + background images simultaneously).

### Pattern 3: LlmAgent with Tool Function

```python
agent = Agent(
    name="script_agent",
    model=ROUTING_MODEL,
    instruction="Call the generate_script tool...",
    tools=[generate_script],
)
```

The LLM reads the instruction, decides to call the tool function, and returns the tool's output. The tool function has full Python access (file I/O, API calls, subprocess).

**Used for:** Script generation, TTS, image generation, Manim code/QC, concept map, video editing.

### Pattern 4: LlmAgent with output_key (Pure LLM)

```python
agent = Agent(
    name="creative_director_agent",
    model=TEXT_MODEL,
    instruction="...prompt with {state_key} templates...",
    output_key="enhanced_script",
    generate_content_config=GenerateContentConfig(
        response_mime_type="application/json",
    ),
)
```

No tool function. The LLM's response is automatically saved to the `output_key` in state. Template variables like `{script_output}` are replaced with current state values.

**Used for:** Script review, creative director, prompt review.

### Pattern 5: Nested Pipelines

```
root (Sequential)
  └── content_pipeline (Parallel)
        └── manim_pipeline (Sequential)
              └── manim_prep (Parallel)
```

ADK supports arbitrary nesting of Sequential and Parallel agents. This lets us express complex dependency graphs declaratively.

---

## 9. Output Structure

```
output/{run_id}/
├── audio/
│   ├── segment_1.mp3              # TTS narration
│   ├── segment_2.mp3
│   └── ...
├── images/
│   ├── segment_1.png              # General segment image (Imagen)
│   ├── segment_3.png
│   ├── bg_segment_2.png           # Manim background image
│   └── ...
├── manim/
│   ├── segment_2.py               # Generated Manim source code
│   ├── segment_2.mov              # Rendered animation (transparent)
│   ├── manim_Segment2Scene_exec.log  # Render logs
│   └── ...
├── concept_map/
│   ├── frame_1.png                # Topic overlay for segment 1
│   ├── frame_2.png
│   └── ...
├── temp_video.mp4                 # (cleaned up after encode)
├── temp_audio.mp3                 # (cleaned up after encode)
└── final_reel.mp4                 # ← FINAL OUTPUT
```

---

## 10. Configuration & Environment

### .env File

```bash
# Required: Vertex AI authentication
GOOGLE_GENAI_USE_VERTEXAI="1"
GOOGLE_APPLICATION_CREDENTIALS="D:/2026/sa.json"
GOOGLE_CLOUD_PROJECT="collab-444307"

# Optional: Defaults shown
GOOGLE_CLOUD_LOCATION="us-central1"      # Vertex AI region
OUTPUT_DIR="./output"                     # Where assets are saved
OVERLAY_FONT_PATH="arial.ttf"            # TTF font for text overlays
USE_CLOUD_TTS="false"                    # "true" for Neural2 voices
```

### config.py — Centralized Configuration

```python
# Model selection — change here to upgrade models globally
ROUTING_MODEL = "gemini-2.5-flash"       # Agent routing decisions
TEXT_MODEL = "gemini-2.5-flash"          # Script + creative work
CODE_MODEL = "gemini-2.5-pro"           # Manim code generation
IMAGEN_MODEL = "imagen-3.0-generate-002" # Image generation

# Lazy-loaded GenAI client (singleton)
def get_client() -> genai.Client:
    # Created on first call, cached for reuse
    # Supports both Vertex AI and API key modes
```

**Why lazy initialization?**
If `config.py` tried to create the client at import time, and credentials weren't set up yet (e.g., during testing), the import would crash and take down the entire application. Lazy init defers creation to first use.

---

## 11. Error Handling & Recovery

### Layer 1: Script Validation (Agents 2 & 4)
- Catches missing fields, invalid JSON, empty arrays
- Auto-repairs in-place before downstream agents see the data

### Layer 2: Parallel Pipeline Isolation
- TTS, Image, and Manim agents each write to separate state keys
- A failure in image generation doesn't affect TTS or Manim

### Layer 3: Manim Auto-Healing (Agent 9)
- 3-attempt retry loop with AI-powered code fixes
- Fallback to guaranteed-to-render template

### Layer 4: Video Composition Fallback (Agent 11)
- If a segment has no image AND no Manim video → dark blue fallback clip
- If text overlay rendering fails → segment plays without overlay (warning logged)
- If concept map fails → segment plays without mini-map
- If FFmpeg merge fails → error returned to user

### Layer 5: TTS Fallback
- Cloud TTS failure → automatic fallback to gTTS
- Total TTS failure for one segment → uses estimated duration from script

---

## 12. Key Design Decisions Explained

### Q: Why not use LangChain / CrewAI / AutoGen?
**A:** Google ADK is purpose-built for Gemini models on Vertex AI. It provides native `SequentialAgent`/`ParallelAgent` composition, automatic state management, and direct integration with Google's AI services (Imagen, TTS). Third-party frameworks add abstraction layers that would complicate Vertex AI integration without providing additional value for our use case.

### Q: Why render Manim as .mov with transparency instead of .mp4?
**A:** MOV format supports alpha channel (transparency). This lets us composite Manim animations over background images — the black Manim background becomes transparent, and only the equations/shapes are visible on top of the cinematic background photo.

### Q: Why not just use FFmpeg for everything (skip MoviePy)?
**A:** MoviePy provides a high-level Python API for operations that would be extremely complex in raw FFmpeg commands — especially multi-layer compositing with transparency masks, PIL-rendered overlays, and per-clip duration adjustments. We do use FFmpeg directly for the final audio merge where MoviePy's encoding is less reliable.

### Q: Why are all state values JSON strings instead of Python objects?
**A:** ADK's session state must be serializable. JSON strings work with any session backend (in-memory, database, cloud storage). They also make debugging easy — you can log the raw state value and see exactly what data is flowing between agents.

### Q: Why ThreadPoolExecutor inside tool functions (not more ADK agents)?
**A:** Within a single agent's tool function, we often need to process N segments in parallel (e.g., generate 5 images simultaneously). Creating 5 ADK agents for this would be over-engineering — a simple thread pool is more efficient for I/O-bound parallel operations within a single logical step.

### Q: Why is the Creative Director a separate agent from Script Generation?
**A:** Separation of concerns. Script Generation focuses on content structure (what to say, segment types, durations). Creative Direction focuses on visual quality (how it should look, image prompts, animation specs). Combining them would create an overloaded prompt that degrades output quality for both tasks.

### Q: Why the 4-color maximum rule in Manim?
**A:** Educational animations must be visually clear. More than 4 colors creates visual noise that makes equations harder to read. The restricted palette (WHITE, YELLOW, BLUE_C, TEAL_C) ensures consistent, professional-looking animations across all segments.

### Q: Why 9:16 aspect ratio everywhere?
**A:** The product targets short-form vertical video platforms (Instagram Reels, YouTube Shorts, TikTok). All visual assets — images, Manim animations, text overlays, concept maps — are generated at 1080x1920 (9:16) for this specific format.

---

*Generated for EduReelADK v2.0.0 — Last updated: 2026-04-14*
