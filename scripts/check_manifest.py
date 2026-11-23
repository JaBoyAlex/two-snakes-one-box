import json
from pathlib import Path
import urllib.request

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://raw.githubusercontent.com/elripalda/RecompLauncher-SDK/main/schema/recomplauncher.json'


def main():
    with urllib.request.urlopen(URL, timeout=30) as response:
        schema = json.load(response)
    manifest = json.loads((ROOT / 'recomplauncher.json').read_text(encoding='utf-8'))
    failures = sorted(jsonschema.Draft7Validator(schema).iter_errors(manifest), key=lambda error: str(error.path))
    if failures:
        raise SystemExit('\n'.join(f'{"/".join(map(str, error.path))}: {error.message}' for error in failures))
    print('RecompLauncher manifest passes the current official JSON schema.')


if __name__ == '__main__':
    main()
