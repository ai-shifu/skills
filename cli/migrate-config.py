"""Apply installer configuration through the profile store's locked transaction."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills/ai-shifu-course-creator/scripts"))
from profile_store import (
    ProfileError, ProfileStore, record_installer_config_root, resolve_installer_config_root,
)


if __name__ == "__main__":
    try:
        default_root = Path(sys.argv[1]).resolve()
        directories = [Path(value) for value in sys.argv[3:]]
        # Keep root selection and pointer publication in one installer-wide
        # transaction, separate from the account transaction at either root.
        selection = ProfileStore(default_root / ".cli-root-selection", default_root / "cli.env")
        with selection._configuration_lock():
            root = resolve_installer_config_root(default_root, directories)
            result = ProfileStore(root, root / "cli.env").import_installer_configuration(
                directories, Path(sys.argv[2]))
            record_installer_config_root(default_root, root)
        result["config_dir"] = str(root)
        print(json.dumps(result))
    except (OSError, ProfileError) as error:
        print(f"Configuration migration failed: {error}", file=sys.stderr)
        sys.exit(1)
