"""Apply installer configuration through the profile store's locked transaction."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills/ai-shifu-course-creator/scripts"))
from profile_store import ProfileError, ProfileStore


if __name__ == "__main__":
    try:
        root = Path(sys.argv[1])
        result = ProfileStore(root, root / "cli.env").import_installer_configuration(
            [Path(value) for value in sys.argv[3:]], Path(sys.argv[2]))
        print(json.dumps(result))
    except (OSError, ProfileError) as error:
        print(f"Configuration migration failed: {error}", file=sys.stderr)
        sys.exit(1)
