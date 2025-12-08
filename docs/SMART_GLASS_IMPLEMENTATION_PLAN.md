

⸻

Handsfree Mode Implementation Plan

This document outlines the development plan for supporting Handsfree Mode in the Roleplaying service.

Overview
	•	Goal: Provide a fully hands-free, voice-driven roleplaying experience across various devices.
	•	Key Features:
	•	Minimal UI with Avatar-focused layout.
	•	Audio cue (Beep) after AI finishes speaking.
	•	Automatic microphone deactivation after 2 seconds of silence.
	•	Device interaction mode differentiation in backend sessions.

⸻

1. Backend (FastAPI)

The backend needs to understand the interaction mode of the client to adjust session behavior such as logging, analytics, or response style.

1.1. Protocol Extension
	•	File: app/roleplaying/handlers/ws_message_models.py
	•	Action: Update InitMessage model.
	•	Detail: Add an optional interactionMode field.

interactionMode: Literal["default", "handsfree"] = "default"



1.2. Session State Management
	•	File: app/roleplaying/core/session_models.py
	•	Action: Update SessionState dataclass.
	•	Detail: Add interaction_mode to store the client’s interaction mode.

1.3. Session Logic Update
	•	File: app/roleplaying/core/session_manager_base.py
	•	Action: Update create_session method.
	•	Detail: Accept interaction_mode parameter and store it in SessionState.

1.4. Handler Integration
	•	File: app/roleplaying/handlers/message_handlers.py
	•	Action: Update handle_init function.
	•	Detail: Extract interactionMode from the InitMessage payload and pass it to session_manager.create_session().

1.5. (Optional) Prompt Engineering
	•	File: app/roleplaying/services/ai_tutor_service.py
	•	Action: Modify system prompt when in hands-free mode.
	•	Detail: When interaction_mode == "handsfree", instruct the LLM to generate shorter, more natural spoken responses optimized for audio-first interactions.

⸻

2. Frontend (Client)

The client is responsible for UI adjustments, audio cues, and silence detection required for hands-free interaction.

2.1. Initialization & Config
	•	Action: Send Interaction Mode.
	•	Detail: When initializing the WebSocket connection, include:

{
  "type": "INIT",
  "interactionMode": "handsfree"
}



2.2. UI/UX Implementation
	•	Layout:
	•	Simplified interface focusing on the Avatar.
	•	Minimal or no text logs, buttons, or manual controls.
	•	Visual Indicators:
	•	Subtle microphone state indicator (e.g., mic-on or mic-off overlay icon).

2.3. Interaction Logic (Handsfree Loop)
	1.	Receive AI Audio: Play the TTS audio from the server.
	2.	Play Cue (Beep):
	•	Triggered immediately after TTS stops.
	•	Plays a short local beep sound to signal “Your turn.”
	3.	Activate Microphone:
	•	Triggered after the beep.
	•	Starts streaming AUDIO_CHUNK messages to backend.
	4.	Silence Detection (VAD):
	•	Continuously monitors user audio input.
	•	If silence lasts 2.0 seconds:
	1.	Stop recording
	2.	Send UTTERANCE_END
	3.	(Optional) Play a “processing…” cue

2.4. Error Handling
	•	Address cases where VAD sensitivity causes early cutoff due to noise.
	•	Allow optional sensitivity adjustments or fallback manual trigger.

⸻

