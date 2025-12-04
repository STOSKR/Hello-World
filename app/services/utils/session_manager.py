"""Session management utilities for browser automation."""

import json
from pathlib import Path
from typing import Optional, Tuple

from app.core.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages browser session loading and merging."""

    def __init__(self, sessions_dir: Path = Path("sessions")):
        self.sessions_dir = sessions_dir
        self.buff_session_path = sessions_dir / "buff_session.json"
        self.steam_session_path = sessions_dir / "steam_session.json"
        self.merged_session_path = sessions_dir / "merged_session.json"

    def has_sessions(self) -> bool:
        return self.buff_session_path.exists() or self.steam_session_path.exists()

    def get_browser_config(self) -> Tuple[bool, Optional[str]]:
        if not self.has_sessions():
            logger.info("using_persistent_context", profile="~/.cs_tracker_profile")
            return True, None

        merged_state = self._merge_sessions()
        use_persistent = False
        storage_state = str(self.merged_session_path)

        logger.info("using_merged_sessions", total_cookies=len(merged_state["cookies"]))
        return use_persistent, storage_state

    def _merge_sessions(self) -> dict:
        merged_state = {"cookies": [], "origins": []}

        if self.buff_session_path.exists():
            with open(self.buff_session_path, "r", encoding="utf-8") as f:
                buff_data = json.load(f)
                merged_state["cookies"].extend(buff_data.get("cookies", []))
                merged_state["origins"].extend(buff_data.get("origins", []))
                logger.info(
                    "loaded_buff_session", cookies=len(buff_data.get("cookies", []))
                )

        if self.steam_session_path.exists():
            with open(self.steam_session_path, "r", encoding="utf-8") as f:
                steam_data = json.load(f)
                merged_state["cookies"].extend(steam_data.get("cookies", []))
                merged_state["origins"].extend(steam_data.get("origins", []))
                logger.info(
                    "loaded_steam_session", cookies=len(steam_data.get("cookies", []))
                )

        with open(self.merged_session_path, "w", encoding="utf-8") as f:
            json.dump(merged_state, f)

        return merged_state
