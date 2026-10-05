import os
import sys
import traceback
from loguru import logger

from preflight.config.settings import settings

def run_hook():
    """
    Main entry point executed by Git via the pre-push shim.
    This function parses Git's stdin stream and strictly enforces the Fail-Open policy.
    """
    try:
        logger.info("Git Pre-Push Hook Triggered by developer.")
        
        # 1. Bypass Checks (CI Environments)
        # We don't want to block automated pipelines with a desktop popup.
        if os.environ.get("CI") == "true" or os.environ.get("PREFLIGHT_BYPASS") == "1":
            logger.info("CI environment or Bypass detected. Skipping AI analysis.")
            sys.exit(0)

        # 2. Read stdin from Git
        # Git passes branch information on stdin in the exact format:
        # <local ref> <local sha1> <remote ref> <remote sha1>
        # There can be multiple lines if the user pushes multiple branches at once.
        raw_refs = sys.stdin.readlines()

        # --- ADD THIS BLOCK ---
        # Reconnect standard input to the terminal so the UI can prompt the developer
        try:
            if os.name == 'nt':
                sys.stdin = open('CON', 'r')
            else:
                sys.stdin = open('/dev/tty', 'r')
        except Exception as e:
            logger.debug(f"Could not reconnect terminal: {e}")
        # ----------------------

        if not raw_refs:
            logger.info("No refs provided by Git on stdin. Allowing push.")
            sys.exit(0)
        
        if not raw_refs:
            logger.info("No refs provided by Git on stdin. Allowing push.")
            sys.exit(0)
            
        logger.debug(f"Received refs from Git: {raw_refs}")

        # 3. Hand off to the Pipeline Orchestrator
        # (Wrapped in an ImportError block so it fails-open while we are still building the app)
        try:
            from preflight.git.ref_parser import parse_refs
            from preflight.pipeline.orchestrator import execute_pipeline
            
            # Parse the raw lines into workable branch data
            parsed_refs = parse_refs(raw_refs)
            
            # Run the AI pipeline, which will eventually return 0 (Continue) or 1 (Cancel)
            exit_code = execute_pipeline(parsed_refs)
            sys.exit(exit_code)
            
        except ImportError as ie:
            logger.warning(f"[Development] Pipeline modules not yet built: {ie}")
            print("\n[Pre-Flight AI] ⚠️  Development Mode: Pipeline incomplete. Allowing push.", file=sys.stderr)
            sys.exit(0)

    except Exception as e:
        # -----------------------------------------------------------------
        # CRITICAL: THE FAIL-OPEN SAFETY NET
        # -----------------------------------------------------------------
        logger.error(f"Fatal Hook Error: {e}")
        logger.error(traceback.format_exc())
        
        # If fail_open is true (default), we print a warning but exit 0 to allow the code upload.
        if settings.fail_open:
            print("\n" + "="*65, file=sys.stderr)
            print("✈️  Pre-Flight AI encountered an internal error.", file=sys.stderr)
            print("🛡️  FAIL-OPEN POLICY ACTIVE: Your git push will CONTINUE.", file=sys.stderr)
            print("="*65 + "\n", file=sys.stderr)
            sys.exit(0) 
        else:
            print("\n[Pre-Flight AI] ❌ Pipeline crashed and fail_open=False. Blocking push.", file=sys.stderr)
            sys.exit(1)
if __name__ == "__main__":
    run_hook()