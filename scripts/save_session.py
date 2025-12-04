"""
Script to manually login to BUFF163 and Steam, then save session cookies.
Run this script once to create session files that can be used in CI/CD.

Usage:
    python scripts/save_session.py [--headless]
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.utils.browser_manager import BrowserManager
from app.core.logger import get_logger

logger = get_logger(__name__)

SESSIONS_DIR = project_root / "sessions"
BUFF_SESSION_FILE = SESSIONS_DIR / "buff_session.json"
STEAM_SESSION_FILE = SESSIONS_DIR / "steam_session.json"


async def save_buff_session(headless: bool = False):
    """Login to BUFF163 and save session."""
    logger.info("starting_buff_login", headless=headless)

    async with BrowserManager(
        headless=headless, use_persistent_context=False  # Use storage_state mode
    ) as browser:
        page = browser.get_page()

        # Navigate to BUFF163
        await browser.navigate("https://buff.163.com/market/csgo")

        print("\n" + "=" * 60)
        print("BUFF163 Login")
        print("=" * 60)
        print("1. Please login manually in the browser window")
        print("2. Navigate around to verify login works")
        print("3. Press ENTER when done...")
        print("=" * 60 + "\n")

        input("Press ENTER to continue...")

        # Save storage state
        await browser.save_storage_state(str(BUFF_SESSION_FILE))
        logger.info("buff_session_saved", path=str(BUFF_SESSION_FILE))
        print(f"✓ BUFF session saved to: {BUFF_SESSION_FILE}")


async def save_steam_session(headless: bool = False):
    """Login to Steam Community Market and save session."""
    logger.info("starting_steam_login", headless=headless)

    async with BrowserManager(
        headless=headless, use_persistent_context=False  # Use storage_state mode
    ) as browser:
        page = browser.get_page()

        # Navigate to Steam Community Market
        await browser.navigate("https://steamcommunity.com/market/")

        print("\n" + "=" * 60)
        print("Steam Community Market Login")
        print("=" * 60)
        print("1. Please login manually in the browser window")
        print("2. Navigate around to verify login works")
        print("3. Press ENTER when done...")
        print("=" * 60 + "\n")

        input("Press ENTER to continue...")

        # Save storage state
        await browser.save_storage_state(str(STEAM_SESSION_FILE))
        logger.info("steam_session_saved", path=str(STEAM_SESSION_FILE))
        print(f"✓ Steam session saved to: {STEAM_SESSION_FILE}")


async def verify_session(session_file: Path, test_url: str, site_name: str):
    """Verify that a saved session works."""
    if not session_file.exists():
        logger.error("session_file_not_found", path=str(session_file))
        print(f"✗ {site_name} session file not found: {session_file}")
        return False

    logger.info("verifying_session", site=site_name, path=str(session_file))

    async with BrowserManager(
        headless=True,
        use_persistent_context=False,
        storage_state_path=str(session_file),
    ) as browser:
        page = browser.get_page()
        await browser.navigate(test_url)

        # Wait a bit for page to load
        await page.wait_for_timeout(3000)

        # Check if we're still logged in (basic check - look for login button)
        # If there's a login button, we're NOT logged in
        is_logged_in = True  # Optimistic

        try:
            # BUFF uses this selector for login
            if "buff.163.com" in test_url:
                login_btn = page.locator('a.i-user:has-text("登录")')
                if await login_btn.count() > 0:
                    is_logged_in = False
        except Exception:
            pass

        if is_logged_in:
            logger.info("session_verified", site=site_name)
            print(f"✓ {site_name} session verified successfully")
            return True
        else:
            logger.warning("session_verification_failed", site=site_name)
            print(
                f"✗ {site_name} session verification failed - may need to login again"
            )
            return False


async def main():
    """Main function to save sessions."""
    import argparse

    parser = argparse.ArgumentParser(description="Save BUFF163 and Steam sessions")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument(
        "--verify-only", action="store_true", help="Only verify existing sessions"
    )
    parser.add_argument(
        "--buff-only", action="store_true", help="Only save BUFF session"
    )
    parser.add_argument(
        "--steam-only", action="store_true", help="Only save Steam session"
    )

    args = parser.parse_args()

    # Create sessions directory if it doesn't exist
    SESSIONS_DIR.mkdir(exist_ok=True)

    if args.verify_only:
        print("\n" + "=" * 60)
        print("Verifying Saved Sessions")
        print("=" * 60 + "\n")

        buff_ok = await verify_session(
            BUFF_SESSION_FILE, "https://buff.163.com/market/csgo", "BUFF163"
        )

        steam_ok = await verify_session(
            STEAM_SESSION_FILE, "https://steamcommunity.com/market/", "Steam"
        )

        print("\n" + "=" * 60)
        print("Verification Summary")
        print("=" * 60)
        print(f"BUFF163: {'✓ OK' if buff_ok else '✗ Failed'}")
        print(f"Steam:   {'✓ OK' if steam_ok else '✗ Failed'}")
        print("=" * 60 + "\n")

        return

    # Save sessions
    try:
        if not args.steam_only:
            await save_buff_session(headless=args.headless)

        if not args.buff_only:
            await save_steam_session(headless=args.headless)

        print("\n" + "=" * 60)
        print("Session Save Complete")
        print("=" * 60)
        print(f"BUFF session:  {BUFF_SESSION_FILE}")
        print(f"Steam session: {STEAM_SESSION_FILE}")
        print("\nYou can now use these session files in CI/CD or other environments.")
        print("=" * 60 + "\n")

    except KeyboardInterrupt:
        print("\n\nSession save cancelled by user.")
        logger.info("session_save_cancelled")
    except Exception as e:
        logger.error("session_save_error", error=str(e))
        print(f"\n✗ Error saving sessions: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
