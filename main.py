#!/usr/bin/env python3
"""
Entry point for the caseworker's-morning agent.

  python3 main.py          runs the agent on the command line (no
                            dependencies beyond the standard library --
                            this is the graded path; see README.md).

  python3 main.py --ui     launches the optional Streamlit viewer
                            instead (requires `pip install -r
                            requirements.txt` first). Not part of the
                            graded floor -- see DECISIONS.md.

Kept as a flag rather than the default so that running this file with
no arguments, on a clean clone, with nothing installed, still works --
that's the mechanical check every submission is put through before a
human looks at anything.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def launch_ui():
    app_path = os.path.join(HERE, "streamlit_app.py")
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path], check=True)
    except FileNotFoundError:
        print("Streamlit isn't installed. Run: pip install -r requirements.txt")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


if __name__ == "__main__":
    if "--ui" in sys.argv:
        launch_ui()
    else:
        from agent.runner import run
        run()
