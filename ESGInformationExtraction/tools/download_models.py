"""
download_models.py
==================
Télécharge les modèles HuggingFace nécessaires sans symlinks (compatible Windows).

Usage :
    python tools/download_models.py

Ce script télécharge les fichiers du modèle GLiNER directement via HTTPS
et les sauvegarde dans .model_cache/ sans passer par le mécanisme de cache
HuggingFace (qui nécessite les symlinks Windows / Developer Mode).
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CACHE = _ROOT / ".model_cache"

MODELS = {
    "gliner_medium_v2": {
        # GLiNER model weights + config
        "repo": "urchade/gliner_medium-v2.1",
        "files": ["gliner_config.json", "model.safetensors"],
        # Tokenizer files come from the DeBERTa-v3-base backbone
        "extra": {
            "repo": "microsoft/deberta-v3-base",
            "files": [
                "config.json",
                "tokenizer_config.json",
                "spm.model",
            ],
        },
    }
}


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> None:
    import urllib.request
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  [skip] {dest.name} déjà présent")
        return
    print(f"  [download] {dest.name}…", end=" ", flush=True)
    try:
        with urllib.request.urlopen(url) as response, dest.open("wb") as out:
            while chunk := response.read(chunk_size):
                out.write(chunk)
        print("OK")
    except Exception as exc:
        print(f"ERREUR ({exc})")
        if dest.exists():
            dest.unlink()
        raise


def download_model(name: str, config: dict) -> Path:
    model_dir = _CACHE / name
    model_dir.mkdir(parents=True, exist_ok=True)

    def _fetch_from(repo: str, files: list[str]) -> list[str]:
        base_url = f"https://huggingface.co/{repo}/resolve/main"
        errors = []
        for filename in files:
            url = f"{base_url}/{filename}"
            try:
                download_file(url, model_dir / filename)
            except Exception as exc:
                errors.append(f"{filename}: {exc}")
        return errors

    print(f"\n--- Téléchargement de {name} ---")
    print(f"  Poids du modèle depuis : {config['repo']}")
    errors = _fetch_from(config["repo"], config["files"])

    if "extra" in config:
        extra = config["extra"]
        print(f"  Tokenizer/config depuis : {extra['repo']}")
        errors += _fetch_from(extra["repo"], extra["files"])

    if errors:
        print(f"  Avertissements : {len(errors)} fichier(s) non téléchargé(s)")
        for e in errors:
            print(f"    - {e}")
    else:
        print(f"  Modèle {name} complet dans {model_dir}")
    return model_dir


def main() -> None:
    print("=== Téléchargement des modèles ESGInformationExtraction ===")
    print(f"Destination : {_CACHE}")
    for name, config in MODELS.items():
        try:
            download_model(name, config)
        except Exception as exc:
            print(f"Erreur fatale pour {name}: {exc}")
            sys.exit(1)
    print("\nTous les modèles sont prêts.")
    print("Les nouveaux modules (gliner_extractor, docling_parser) vont les utiliser automatiquement.")


if __name__ == "__main__":
    main()
