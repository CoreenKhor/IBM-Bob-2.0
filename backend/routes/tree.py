"""
GET /api/tree

Returns the file tree of the demo/ecommerce sample codebase.
"""

import os
from flask import Blueprint, current_app, jsonify

tree_bp = Blueprint("tree", __name__)

DEMO_PATH = os.environ.get(
    "DEMO_CODEBASE_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "demo", "ecommerce"),
)


def _build_tree(root: str) -> list[dict]:
    """Walk the demo directory and return a flat list of file/dir entries."""
    entries = []
    abs_root = os.path.realpath(root)

    for dirpath, dirnames, filenames in os.walk(abs_root):
        # Skip __pycache__ and hidden dirs
        dirnames[:] = [d for d in sorted(dirnames) if not d.startswith((".", "__"))]

        rel_dir = os.path.relpath(dirpath, abs_root)
        if rel_dir != ".":
            entries.append({"path": rel_dir.replace("\\", "/"), "type": "dir"})

        for fname in sorted(filenames):
            if fname.startswith("."):
                continue
            rel_file = os.path.relpath(
                os.path.join(dirpath, fname), abs_root
            ).replace("\\", "/")
            entries.append({"path": rel_file, "type": "file"})

    return entries


@tree_bp.get("/tree")
def get_tree():
    demo_root = os.path.realpath(
        os.path.join(os.path.dirname(__file__), DEMO_PATH)
        if not os.path.isabs(DEMO_PATH)
        else DEMO_PATH
    )

    if not os.path.isdir(demo_root):
        return jsonify({"error": f"Demo codebase not found at: {demo_root}"}), 404

    return jsonify({"root": "demo/ecommerce", "files": _build_tree(demo_root)})
