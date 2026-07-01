"""
Image-dataset utilities for the folder-per-class zip format.

Two levels of checking, used in two places:
  - inspect_structure(): cheap, no image decoding. Run synchronously at upload
    to reject obviously-broken zips fast (not a zip, too big, <2 class folders).
  - validate_contents(): opens every image to confirm it decodes. Run by the
    background validation task, where O(n) work is fine.

Both raise ValueError with a human-readable message on failure; the API turns
that into a 400 and the worker records it as the dataset's error.
"""

import io
import posixpath
import zipfile
from collections.abc import Iterator

from PIL import Image

# Image file extensions we recognize inside an uploaded zip.
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
# Reject zips that expand to more than this (zip-bomb guard).
MAX_UNZIPPED_BYTES = 500 * 1024 * 1024  # 500 MB


def _open(raw_bytes: bytes) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(io.BytesIO(raw_bytes))
    except zipfile.BadZipFile:
        raise ValueError("Uploaded file is not a valid .zip")


def _candidates(zf: zipfile.ZipFile) -> Iterator[tuple[str, str]]:
    """Yield (entry_name, class_label) for image-looking files in class folders.

    The label is the image's immediate parent folder, so both `cats/x.jpg` and
    `wrapper/cats/x.jpg` map to "cats". Junk (dirs, __MACOSX, dotfiles, non-image
    extensions, images at the zip root) is skipped.
    """
    for name in zf.namelist():
        if name.endswith("/") or "__MACOSX" in name:
            continue
        base = posixpath.basename(name)
        if not base or base.startswith("."):
            continue
        if posixpath.splitext(base)[1].lower() not in IMAGE_EXTS:
            continue
        label = posixpath.basename(posixpath.dirname(name))
        if not label:  # image at the zip root, no class folder
            continue
        yield name, label


def inspect_structure(raw_bytes: bytes) -> dict:
    """Cheap structural check (no decoding) for the upload request."""
    zf = _open(raw_bytes)
    if sum(i.file_size for i in zf.infolist()) > MAX_UNZIPPED_BYTES:
        mb = MAX_UNZIPPED_BYTES // (1024 * 1024)
        raise ValueError(f"Image zip expands to over {mb} MB uncompressed, too large")

    counts: dict[str, int] = {}
    for _name, label in _candidates(zf):
        counts[label] = counts.get(label, 0) + 1

    if len(counts) < 2:
        raise ValueError(
            "Image zip must use a folder-per-class layout with at least 2 class "
            "folders, each containing images (e.g. cats/…, dogs/…)"
        )
    return {
        "classes": sorted(counts),
        "num_classes": len(counts),
        "num_images": sum(counts.values()),
    }


def validate_contents(raw_bytes: bytes) -> dict:
    """Full content validation: open every image, drop the ones that don't decode.

    Returns final metadata (counting only valid images). Raises ValueError if
    fewer than 2 classes are left with valid images.
    """
    zf = _open(raw_bytes)
    counts: dict[str, int] = {}
    skipped = 0
    for name, label in _candidates(zf):
        try:
            with Image.open(io.BytesIO(zf.read(name))) as img:
                img.verify()
        except Exception:
            skipped += 1
            continue
        counts[label] = counts.get(label, 0) + 1

    if len(counts) < 2:
        raise ValueError(
            "Fewer than 2 classes contain valid images — is this an image dataset?"
        )
    return {
        "classes": sorted(counts),
        "num_classes": len(counts),
        "num_images": sum(counts.values()),
        "skipped_invalid": skipped,
    }
