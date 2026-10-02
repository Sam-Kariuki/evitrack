import hashlib
import os
import uuid

ALLOWED_EXTENSIONS = {
    "txt", "log", "csv", "json", "pdf", "png", "jpg", "jpeg", "gif",
    "docx", "xlsx", "zip", "eml", "sqlite", "db", "raw", "dd", "img",
    "mem", "bin",
}
CHUNK_SIZE = 64 * 1024


def allowed_file(filename):
    """True if the (already sanitised) name has an allowlisted extension."""
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def sha256_of_file(path):
    """Hash a file on disk in chunks and return the hex digest."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_upload(file_storage, upload_folder):
    """Stream an upload to disk under a random name, hashing as it goes.

    Returns (stored_name, sha256_hex, size_in_bytes).
    """
    stored_name = uuid.uuid4().hex
    path = os.path.join(upload_folder, stored_name)
    digest = hashlib.sha256()
    size = 0
    try:
        with open(path, "xb") as out:  # "x" refuses to overwrite an existing file
            while True:
                chunk = file_storage.stream.read(CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
                out.write(chunk)
                size += len(chunk)
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise
    return stored_name, digest.hexdigest(), size