"""Convenience script to run the full pipeline."""
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "parse":
        from src.parser.cli import main
        main()
    elif len(sys.argv) > 1 and sys.argv[1] == "web":
        from src.webui.app import app
        app.run(debug=True, port=5000)
    else:
        print("Usage:")
        print("  python run.py parse <pdf_path> [output_json]  - Parse PDF to JSON")
        print("  python run.py web                            - Start web UI")
