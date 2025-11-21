#!/usr/bin/env python3
"""
Text-based Roleplaying Test Client
===================================
WebSocket client for testing roleplaying sessions without audio/STT.

Usage:
    python scripts/test_text_roleplay.py --user-id 1 --scenario-id 1
    python scripts/test_text_roleplay.py  # Uses defaults

Commands:
    - Type text to send USER_TEXT message
    - Type /quit to end session
    - Ctrl+C to disconnect

Environment:
    SESSION_API_URL: Session creation endpoint (default: http://localhost:8001/roleplaying/sessions)
"""

import argparse
import asyncio
import json
import logging
import shutil
import sys
import textwrap
import time
from typing import Optional

import httpx
import websockets
from websockets.client import WebSocketClientProtocol

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RoleplayTestClient:
    """Text-based roleplaying test client"""

    def __init__(
        self,
        user_id: int,
        scenario_id: int,
        session_api_url: str = "http://localhost:8000/roleplaying/sessions",
    ):
        self.user_id = user_id
        self.scenario_id = scenario_id
        self.session_api_url = session_api_url
        self.session_id_override: Optional[str] = None
        self.session_id: Optional[str] = None
        self.ws_url: Optional[str] = None
        self.scenario: Optional[dict] = None
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.terminal_width = shutil.get_terminal_size((80, 24)).columns
        self.last_user_send_time: Optional[float] = None
        self.session_end_reason: Optional[str] = None

    def _format_ai_message(self, text: str, label: str = "AI") -> str:
        """Format AI message (left-aligned)"""
        max_width = min(self.terminal_width - 10, 70)
        wrapped = textwrap.fill(text, width=max_width)
        lines = wrapped.split("\n")
        formatted = f"\n[{label}] {lines[0]}"
        for line in lines[1:]:
            formatted += f"\n      {line}"
        return formatted

    def _format_user_message(self, text: str) -> str:
        """Format user message (right-aligned)"""
        max_width = min(self.terminal_width - 10, 70)
        wrapped = textwrap.fill(text, width=max_width)
        lines = wrapped.split("\n")
        formatted_lines = []
        for i, line in enumerate(lines):
            if i == 0:
                label = "[You] "
                padding = self.terminal_width - len(label) - len(line) - 1
                formatted_lines.append(" " * max(0, padding) + label + line)
            else:
                padding = self.terminal_width - len(line) - 7
                formatted_lines.append(" " * max(0, padding) + "      " + line)
        return "\n" + "\n".join(formatted_lines)

    async def create_session(self) -> bool:
        """Create roleplaying session via HTTP API"""
        logger.info(
            f"Creating session for user_id={self.user_id}, scenario_id={self.scenario_id}"
        )

        try:
            async with httpx.AsyncClient() as client:
                payload = {"userId": self.user_id, "scenarioId": self.scenario_id}
                if self.session_id_override:
                    payload["sessionId"] = self.session_id_override

                response = await client.post(
                    self.session_api_url,
                    json=payload,
                    timeout=10.0,
                )

                if response.status_code != 200:
                    logger.error(
                        f"Session creation failed: {response.status_code} - {response.text}"
                    )
                    return False

                data = response.json()
                self.session_id = data.get("session_id")
                self.ws_url = data.get("ws_url")
                self.scenario = data.get("scenario")

                logger.info(f"Session created: {self.session_id}")
                logger.info(f"WebSocket URL: {self.ws_url}")
                logger.info(f"Scenario: {self.scenario.get('title')}")
                logger.info(
                    f"Roles: {self.scenario.get('myRole')} → {self.scenario.get('aiRole')}"
                )

                return True

        except httpx.RequestError as e:
            logger.error(f"HTTP request failed: {e}")
            return False

        except Exception as e:
            logger.error(f"Session creation error: {e}", exc_info=True)
            return False

    async def connect_websocket(self) -> bool:
        """Connect to WebSocket and send INIT message"""
        if not self.ws_url:
            logger.error("No WebSocket URL available")
            return False

        try:
            # Convert http://... to ws://...
            ws_url = self.ws_url.replace("http://", "ws://").replace(
                "https://", "wss://"
            )
            logger.info(f"Connecting to WebSocket: {ws_url}")

            self.websocket = await websockets.connect(ws_url)
            logger.info("WebSocket connected")

            # Send INIT message
            init_message = {
                "type": "INIT",
                "userId": self.user_id,
                "subjectId": self.scenario["subjectId"],
                "myRole": self.scenario["myRole"],
                "aiRole": self.scenario["aiRole"],
                "fixedQuestions": self.scenario["fixedQuestions"],
            }

            await self.websocket.send(json.dumps(init_message))
            logger.info("INIT message sent")

            # Wait for ACK and first AI question
            while True:
                response = await self.websocket.recv()
                message = json.loads(response)
                msg_type = message.get("type")

                if msg_type == "ACK":
                    logger.info(f"Received ACK: {message.get('message')}")

                elif msg_type == "AI_TEXT":
                    text = message.get("text")
                    # Format and print first AI question (left-aligned)
                    print(self._format_ai_message(text))
                    break

                elif msg_type == "ERROR":
                    logger.error(f"Server error: {message.get('message')}")
                    return False

            return True

        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            return False

    async def send_text(self, text: str):
        """Send USER_TEXT message"""
        if not self.websocket:
            logger.error("WebSocket not connected")
            return

        message = {"type": "USER_TEXT", "text": text}
        await self.websocket.send(json.dumps(message))
        self.last_user_send_time = time.time()
        logger.debug(f"Sent USER_TEXT: {text[:50]}...")

    async def receive_messages(self):
        """Receive and print messages from server"""
        if not self.websocket or self.session_end_reason:
            return

        try:
            while True:
                # Remove timeout - wait indefinitely for server response
                response = await self.websocket.recv()
                message = json.loads(response)
                msg_type = message.get("type")

                if msg_type == "AI_TYPING":
                    print("\n💭 AI is thinking...")

                elif msg_type == "AI_TEXT":
                    # Calculate AI response time
                    elapsed_time = None
                    if self.last_user_send_time is not None:
                        elapsed_time = time.time() - self.last_user_send_time
                        self.last_user_send_time = None

                    text = message.get("text")
                    is_fixed = message.get("is_fixed_question", False)

                    # Format and print AI message (left-aligned)
                    print(self._format_ai_message(text))

                    # Log AI response time
                    if elapsed_time is not None:
                        logger.info(f"AI response generated in {elapsed_time:.2f}s")
                        print(f"      ⏱️  {elapsed_time:.2f}s")

                    # Return after receiving AI response
                    break

                elif msg_type == "ERROR":
                    error_msg = message.get("message")
                    print(f"\n❌ [ERROR] {error_msg}")
                    logger.error(f"Server error: {error_msg}")

                elif msg_type == "SESSION_ENDED":
                    reason = message.get("reason")
                    self.session_end_reason = reason or "unknown"
                    print(f"\n[SESSION ENDED] Reason: {self.session_end_reason}")
                    break

                else:
                    logger.debug(f"Received message: {msg_type}")

        except websockets.exceptions.ConnectionClosed:
            if not self.session_end_reason:
                self.session_end_reason = "connection_closed"
            logger.info("WebSocket connection closed")

        except Exception as e:
            logger.error(f"Error receiving messages: {e}", exc_info=True)

    async def end_session(self):
        """Send END_SESSION message"""
        if not self.websocket:
            return

        try:
            message = {"type": "END_SESSION"}
            await self.websocket.send(json.dumps(message))
            logger.info("END_SESSION message sent")

            # Wait for SESSION_ENDED response
            await self.receive_messages()

        except Exception as e:
            logger.error(f"Error ending session: {e}")

    async def interactive_loop(self):
        """Interactive conversation loop"""
        print("\n" + "=" * 60)
        print("Text-based Roleplaying Session Started")
        print("=" * 60)
        print(f"Scenario: {self.scenario.get('title')}")
        print(f"Your Role: {self.scenario.get('myRole')}")
        print(f"AI Role: {self.scenario.get('aiRole')}")
        print("\nType your responses in English, or '/quit' to end session.")
        print("=" * 60)

        try:
            while True:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\n[You] "
                )

                # Check for quit command
                if user_input.strip().lower() == "/quit":
                    print("\nEnding session...")
                    await self.end_session()
                    break

                # Skip empty input
                if not user_input.strip():
                    continue

                # Display user message (right-aligned)
                print(self._format_user_message(user_input))

                # Send user text
                await self.send_text(user_input)

                # Receive AI response
                await self.receive_messages()

                if self.session_end_reason:
                    break

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Closing connection...")
            await self.end_session()

        except Exception as e:
            logger.error(f"Interactive loop error: {e}", exc_info=True)
        finally:
            if self.session_end_reason:
                print(f"\n✅ Session finished (reason: {self.session_end_reason})")

    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("WebSocket closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")

    async def run(self):
        """Run the test client"""
        try:
            # Step 1: Create session
            if not await self.create_session():
                logger.error("Failed to create session. Exiting.")
                return 1

            # Step 2: Connect WebSocket
            if not await self.connect_websocket():
                logger.error("Failed to connect WebSocket. Exiting.")
                return 1

            # Step 3: Interactive loop
            await self.interactive_loop()

            # Step 4: Close connection
            await self.close()

            print("\nSession ended successfully.")
            return 0

        except Exception as e:
            logger.error(f"Test client error: {e}", exc_info=True)
            return 1


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Text-based roleplaying test client (without audio/STT)"
    )
    parser.add_argument("--user-id", type=int, default=1, help="User ID (default: 1)")
    parser.add_argument(
        "--scenario-id", type=int, default=1, help="Scenario ID (default: 1)"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8001/roleplaying/sessions",
        help="Session API URL (default: http://localhost:8001/roleplaying/sessions)",
    )
    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Session ID to reuse (FastAPI will accept this instead of generating UUID)",
    )

    args = parser.parse_args()

    # Create and run test client
    client = RoleplayTestClient(
        user_id=args.user_id, scenario_id=args.scenario_id, session_api_url=args.api_url
    )
    client.session_id_override = args.session_id

    exit_code = await client.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
