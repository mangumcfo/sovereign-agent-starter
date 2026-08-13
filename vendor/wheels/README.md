# vendor/wheels — offline install cache (P0-2, cold/hotspot stand-up)

A cold machine on a phone hotspot cannot reach the pip index. The crypto substrate
(`breathline_primitives`) already ships in-tree; the only network dependency left in
`pip install -e .` is resolving **flask + pyyaml (+ transitives)** from PyPI.

Populate this directory ONCE on a networked machine:

    scripts/vendor_wheels.sh          # core runtime
    scripts/vendor_wheels.sh --dev    # + pytest / cryptography (to run the suite offline)

Then carry the repo (with this directory filled) to the cold machine and install with no index:

    python3 -m venv .venv && . .venv/bin/activate
    pip install --no-index --find-links vendor/wheels -e .

`scripts/stand_up_node.sh --offline` does exactly this automatically when wheels are present.

Wheels are platform + Python-minor specific — vendor on a machine matching the cold one.
The `.whl` / `.tar.gz` files are git-ignored (see `.gitignore`); ship them in the release
tarball, not in git history. This directory (and this README) are tracked so the path exists.
