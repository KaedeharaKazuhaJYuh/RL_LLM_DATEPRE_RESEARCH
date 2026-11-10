"""Verify repeated DAComp-DE starting database states via HTTP byte ranges.

Only the ZIP central directory and repeated start-database members are read.
Database contents are streamed through hashes and never written to disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import urllib.request
import zlib
from collections import defaultdict
from pathlib import Path


REVISION = "8c4a18983b0733256fffb593f7febb9ab6697854"
ARCHIVE_SIZE = 2_267_093_861
ARCHIVE_FILE_GIT_OID = "74455f15c5ec267a729201547c383d74f803697e"
ARCHIVE_URL = (
    "https://huggingface.co/datasets/DAComp/dacomp-de/resolve/"
    f"{REVISION}/dacomp-de.zip"
)
START_DB_RE = re.compile(r"dacomp-de-(?:impl|evol)-\d{3}/[^/]*_start\.duckdb$")


def get_range(start: int, end: int) -> bytes:
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        expected = f"bytes {start}-{end}/{ARCHIVE_SIZE}"
        content_range = response.headers.get("Content-Range", "")
        if response.status != 206 or content_range != expected:
            raise RuntimeError(
                f"range rejected: status={response.status}, content_range={content_range!r}"
            )
        data = response.read()
    if len(data) != end - start + 1:
        raise RuntimeError(f"short range read: expected {end-start+1}, got {len(data)}")
    return data


def archive_entries() -> list[dict[str, int | str]]:
    tail = get_range(ARCHIVE_SIZE - 65_557, ARCHIVE_SIZE - 1)
    eocd_offset = tail.rfind(b"PK\x05\x06")
    if eocd_offset < 0:
        raise RuntimeError("ZIP end-of-central-directory record not found")
    eocd = struct.unpack_from("<4s4H2LH", tail, eocd_offset)
    _, disk, cd_disk, disk_entries, entry_count, cd_size, cd_offset, _ = eocd
    if disk or cd_disk or disk_entries != entry_count:
        raise RuntimeError("multi-disk or inconsistent ZIP directory is unsupported")
    if entry_count == 0xFFFF or cd_size == 0xFFFFFFFF or cd_offset == 0xFFFFFFFF:
        raise RuntimeError("ZIP64 archive directory is unsupported")

    directory = get_range(cd_offset, cd_offset + cd_size - 1)
    entries: list[dict[str, int | str]] = []
    offset = 0
    while offset < len(directory):
        fields = struct.unpack_from("<4s6H3L5H2L", directory, offset)
        if fields[0] != b"PK\x01\x02":
            raise RuntimeError(f"bad central-directory record at byte {offset}")
        flags, method = fields[3], fields[4]
        crc32, compressed_size, uncompressed_size = fields[7:10]
        name_length, extra_length, comment_length = fields[10:13]
        name_bytes = directory[offset + 46 : offset + 46 + name_length]
        encoding = "utf-8" if flags & 0x800 else "cp437"
        name = name_bytes.decode(encoding)
        local_offset = fields[16]
        if START_DB_RE.fullmatch(name):
            if any(value == 0xFFFFFFFF for value in (compressed_size, uncompressed_size, local_offset)):
                raise RuntimeError(f"ZIP64 member not supported: {name}")
            entries.append(
                {
                    "name": name,
                    "flags": flags,
                    "method": method,
                    "crc32": crc32,
                    "compressed_size": compressed_size,
                    "uncompressed_size": uncompressed_size,
                    "local_offset": local_offset,
                }
            )
        offset += 46 + name_length + extra_length + comment_length
    if offset != len(directory):
        raise RuntimeError("central-directory size did not match parsed records")
    return entries


def member_sha256(entry: dict[str, int | str]) -> tuple[str, str]:
    local_offset = int(entry["local_offset"])
    header = get_range(local_offset, local_offset + 29)
    fields = struct.unpack("<4s5H3L2H", header)
    signature, flags, method = fields[0], fields[2], fields[3]
    name_length, extra_length = fields[9:11]
    if signature != b"PK\x03\x04":
        raise RuntimeError(f"bad local file header: {entry['name']}")
    if method != entry["method"]:
        raise RuntimeError(f"compression method differs from directory: {entry['name']}")
    if (flags ^ int(entry["flags"])) & 0x1:
        raise RuntimeError(f"encryption flag differs from directory: {entry['name']}")
    data_start = local_offset + 30 + name_length + extra_length
    compressed_size = int(entry["compressed_size"])
    compressed = get_range(data_start, data_start + compressed_size - 1)
    method = int(entry["method"])
    if method == 0:
        content = compressed
    elif method == 8:
        content = zlib.decompress(compressed, -15)
    else:
        raise RuntimeError(f"unsupported ZIP compression method {method}: {entry['name']}")

    if len(content) != int(entry["uncompressed_size"]):
        raise RuntimeError(f"uncompressed size mismatch: {entry['name']}")
    crc = zlib.crc32(content) & 0xFFFFFFFF
    if crc != int(entry["crc32"]):
        raise RuntimeError(f"CRC-32 mismatch: {entry['name']}")
    return hashlib.sha256(content).hexdigest(), hashlib.sha256(compressed).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("DAComp_START_STATE_SHA256_2026_11_06.json"),
    )
    args = parser.parse_args()

    entries = archive_entries()
    groups: dict[tuple[int, int], list[dict[str, int | str]]] = defaultdict(list)
    for entry in entries:
        groups[(int(entry["crc32"]), int(entry["uncompressed_size"]))].append(entry)
    repeated = [members for members in groups.values() if len(members) > 1]
    bytes_to_read = sum(int(entry["compressed_size"]) for group in repeated for entry in group)

    results = []
    for group_number, group in enumerate(repeated, start=1):
        members = []
        for entry in group:
            raw_sha256, compressed_sha256 = member_sha256(entry)
            members.append(
                {
                    "path": entry["name"],
                    "uncompressed_size": entry["uncompressed_size"],
                    "crc32": f"{int(entry['crc32']):08x}",
                    "sha256": raw_sha256,
                    "compressed_sha256": compressed_sha256,
                }
            )
            print(f"[{group_number}/{len(repeated)}] verified {entry['name']}", flush=True)
        raw_hashes = {member["sha256"] for member in members}
        results.append(
            {
                "members": members,
                "byte_identical": len(raw_hashes) == 1,
                "signature_collision": len(raw_hashes) != 1,
            }
        )

    record = {
        "dataset_revision": REVISION,
        "archive_size": ARCHIVE_SIZE,
        "archive_file_git_oid": ARCHIVE_FILE_GIT_OID,
        "method": "HTTP range reads of ZIP central directory and repeated start database members; no database files persisted",
        "start_database_count": len(entries),
        "crc32_size_signature_count": len(groups),
        "repeated_signature_groups": len(repeated),
        "repeated_member_count": sum(len(group) for group in repeated),
        "compressed_bytes_read_for_repeated_members": bytes_to_read,
        "groups": results,
    }
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "start_database_count": record["start_database_count"],
                "signature_count": record["crc32_size_signature_count"],
                "repeated_groups": record["repeated_signature_groups"],
                "repeated_members": record["repeated_member_count"],
                "compressed_bytes_read": bytes_to_read,
                "all_repeated_groups_byte_identical": all(
                    group["byte_identical"] for group in results
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
