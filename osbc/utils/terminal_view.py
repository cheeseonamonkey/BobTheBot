import os
import subprocess
import time
import argparse

def main():
    parser = argparse.ArgumentParser(description="Terminal screen viewer using Chafa.")
    parser.add_argument("--display", default=":99", help="X display to view (default: :99)")
    parser.add_argument("--size", default="80x40", help="Chafa output size (default: 80x40)")
    parser.add_argument("--fps", type=float, default=2.0, help="Frames per second (default: 2.0)")
    args = parser.parse_args()

    env = os.environ.copy()
    env["DISPLAY"] = args.display
    tmp_img = "/tmp/osbc_view.png"

    print(f"Starting OSBC Terminal Viewer on {args.display}...")
    try:
        while True:
            # Capture screen using ImageMagick 'import' (very common, usually installed)
            # or we could use 'mss' for a more efficient but needs a bit more code to save png
            subprocess.run(["import", "-window", "root", tmp_img], env=env, check=True)
            # Clear terminal or use ANSI escapes to redraw
            # os.system('clear') # Too flickery
            # Better: use CSI H to home cursor
            print("\033[H", end="")
            subprocess.run(["chafa", "--size", args.size, tmp_img])
            time.sleep(1.0 / args.fps)
    except KeyboardInterrupt:
        print("\nExiting Terminal Viewer.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
