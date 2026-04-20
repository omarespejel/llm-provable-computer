#!/usr/bin/env python3
"""Generate deterministic adversarial mutations for Phase 37 receipt artifacts.

This script is intentionally schema-tolerant and self-contained:
- it only uses the Python standard library;
- it does not import any Rust verifier code;
- it emits one mutated JSON artifact per mutation plus a manifest;
- it only performs a generic commitment recomputation when the receipt already
  exposes a local material field that can be hashed without verifier logic.

The generator is meant for hardening and regression testing. It should stay
disjoint from the verifier implementation under tools/reference_verifier.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Callable
from typing import Any, Iterable, Iterator, Sequence


UNKNOWN_FIELD_KEY = "__phase37_unknown_field__"
MANIFEST_NAME = "phase37_bad_manifest.json"

FALSE_CLAIM_KEY_HINTS = (
    "claim_is_valid",
    "claim_valid",
    "claim_verified",
    "claim_passes",
    "proof_claim",
    "false_claim",
    "claim_flag",
    "claim",
    "valid",
    "pass",
    "succeed",
)

FALSE_CLAIM_EXACT_NAMES = ("claim_is_valid", "claim_valid", "claim_verified", "claim_passes")
SOURCE_BINDING_EXACT_NAMES = (
    "source_binding_verified",
    "source_binding",
    "source_bound",
    "source_linked",
)
HASH_EXACT_NAMES = ("receipt_hash", "artifact_hash", "proof_hash", "hash", "digest", "checksum")
FINAL_COMMITMENT_EXACT_NAMES = (
    "final_commitment",
    "output_commitment",
    "receipt_commitment",
    "root_commitment",
)
SOURCE_COMMITMENT_EXACT_NAMES = (
    "source_commitment",
    "source_binding_commitment",
    "source_root_commitment",
    "claimed_source_commitment",
)

SOURCE_BINDING_KEY_HINTS = (
    "source_binding_verified",
    "source_binding",
    "source_bound",
    "source_linked",
    "binding_verified",
    "bound_to_source",
    "source",
    "binding",
    "bound",
    "linked",
)

HASH_KEY_HINTS = ("hash", "digest", "checksum", "commitment")
FINAL_COMMITMENT_KEY_HINTS = (
    "final_commitment",
    "output_commitment",
    "receipt_commitment",
    "root_commitment",
    "commitment",
)
SOURCE_COMMITMENT_KEY_HINTS = (
    "source_commitment",
    "source_binding_commitment",
    "source_root_commitment",
    "claimed_source_commitment",
    "source",
    "commitment",
)
REQUIRED_FIELD_KEY_HINTS = (
    "required_field",
    "receipt_version",
    "phase",
    "layout_commitment",
    "source_binding_verified",
    "source_binding",
    "claim_is_valid",
    "claim_valid",
    "final_commitment",
    "source_commitment",
)
MATERIAL_KEY_HINTS = (
    "final_commitment_material",
    "receipt_commitment_material",
    "commitment_material",
)

HEX_RE = re.compile(r"^(?:0x)?[0-9a-f]+$")


@dataclass(frozen=True)
class MutationResult:
    name: str
    file_name: str
    path: list[Any] | None
    before: Any
    after: Any
    note: str
    recomputed_final_commitment: bool = False
    recompute_basis_path: list[Any] | None = None


def _as_jsonable_path(path: Sequence[Any] | None) -> list[Any] | None:
    if path is None:
        return None
    return [token for token in path]


def sha256_file(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def stable_json_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def load_json(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: pathlib.Path, value: Any) -> None:
    path.write_text(stable_json_text(value), encoding="utf-8")


def walk_entries(node: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[tuple[Any, ...], Any, Any]]:
    if isinstance(node, dict):
        for key in sorted(node):
            value = node[key]
            next_path = path + (key,)
            yield next_path, key, value
            yield from walk_entries(value, next_path)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            next_path = path + (index,)
            yield next_path, index, value
            yield from walk_entries(value, next_path)


def get_in(node: Any, path: Sequence[Any]) -> Any:
    current = node
    for token in path:
        current = current[token]
    return current


def set_in(node: Any, path: Sequence[Any], value: Any) -> None:
    if not path:
        raise ValueError("cannot set the root node in place")
    parent = get_in(node, path[:-1])
    parent[path[-1]] = value


def delete_in(node: Any, path: Sequence[Any]) -> None:
    if not path:
        raise ValueError("cannot delete the root node")
    parent = get_in(node, path[:-1])
    del parent[path[-1]]


def find_first_path(
    root: Any,
    *,
    predicate: Callable[[Sequence[Any], Any, Any], bool],
) -> tuple[Any, ...] | None:
    candidates: list[tuple[Any, ...]] = []
    for path, key, value in walk_entries(root):
        if predicate(path, key, value):
            candidates.append(path)
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: (len(candidate), candidate))


def key_contains_any(key: Any, hints: Iterable[str]) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(hint in lowered for hint in hints)


def path_tail_lower(path: Sequence[Any]) -> str:
    for token in reversed(path):
        if isinstance(token, str):
            return token.lower()
    return ""


def bool_flag_predicate(desired_value: bool, hints: tuple[str, ...]):
    def _predicate(path: Sequence[Any], key: Any, value: Any) -> bool:
        if not isinstance(value, bool) or value is not desired_value:
            return False
        return key_contains_any(key, hints)

    return _predicate


def string_predicate(
    *,
    hints: tuple[str, ...],
    require_hex_like: bool = False,
    require_lowercase_change: bool = False,
) :
    def _predicate(path: Sequence[Any], key: Any, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        if not key_contains_any(key, hints):
            return False
        if require_hex_like and not HEX_RE.fullmatch(value):
            return False
        if require_lowercase_change and value == value.upper():
            return False
        return True

    return _predicate


def find_bool_path(root: Any, desired_value: bool, hints: tuple[str, ...]) -> tuple[Any, ...] | None:
    return find_first_path(root, predicate=bool_flag_predicate(desired_value, hints))


def find_string_path(root: Any, hints: tuple[str, ...], *, require_hex_like: bool = False, require_lowercase_change: bool = False) -> tuple[Any, ...] | None:
    return find_first_path(
        root,
        predicate=string_predicate(
            hints=hints,
            require_hex_like=require_hex_like,
            require_lowercase_change=require_lowercase_change,
        ),
    )


def find_required_field_path(root: Any) -> tuple[Any, ...] | None:
    for exact_name in REQUIRED_FIELD_KEY_HINTS:
        path = find_first_path(
            root,
            predicate=lambda _path, key, _value, exact_name=exact_name: isinstance(key, str)
            and key.lower() == exact_name,
        )
        if path is not None:
            return path
    return None


def find_path_by_exact_names(
    root: Any,
    exact_names: Sequence[str],
    *,
    value_predicate: Callable[[Any], bool] | None = None,
) -> tuple[Any, ...] | None:
    for exact_name in exact_names:
        path = find_first_path(
            root,
            predicate=lambda _path, key, value, exact_name=exact_name: isinstance(key, str)
            and key.lower() == exact_name
            and (value_predicate(value) if value_predicate is not None else True),
        )
        if path is not None:
            return path
    return None


def tamper_hex_string(value: str) -> str:
    prefix = ""
    body = value
    if body.startswith(("0x", "0X")):
        prefix = body[:2]
        body = body[2:]
    if not body:
        raise ValueError("cannot tamper an empty hex string")
    last = body[-1].lower()
    replacement = "0" if last != "0" else "1"
    tampered = body[:-1] + replacement
    if tampered == body:
        tampered = body[:-1] + ("f" if last != "f" else "e")
    return prefix + tampered


def uppercase_hash(value: str) -> str:
    result = value.upper()
    if result == value:
        raise ValueError("selected hash is already uppercase")
    return result


def format_digest_like(template: str, digest_hex: str) -> str:
    return f"0x{digest_hex}" if template.startswith(("0x", "0X")) else digest_hex


def find_material_path(root: Any) -> tuple[Any, ...] | None:
    for hint in MATERIAL_KEY_HINTS:
        path = find_first_path(
            root,
            predicate=lambda _path, key, _value, hint=hint: isinstance(key, str)
            and key.lower() == hint,
        )
        if path is not None:
            return path
    return None


def mutate_flag(
    receipt: Any,
    *,
    desired_value: bool,
    hints: tuple[str, ...],
    name: str,
    file_name: str,
    note: str,
) -> MutationResult:
    exact_names = FALSE_CLAIM_EXACT_NAMES if desired_value is False else SOURCE_BINDING_EXACT_NAMES
    path = find_path_by_exact_names(
        receipt,
        exact_names,
        value_predicate=lambda value: isinstance(value, bool) and value is desired_value,
    )
    if path is None:
        path = find_bool_path(receipt, desired_value, hints)
    if path is None:
        raise SystemExit(f"could not find a boolean field for mutation {name!r}")
    mutated = copy.deepcopy(receipt)
    before = get_in(mutated, path)
    set_in(mutated, path, not before)
    return MutationResult(
        name=name,
        file_name=file_name,
        path=_as_jsonable_path(path),
        before=before,
        after=not before,
        note=note,
    )


def mutate_string(
    receipt: Any,
    *,
    hints: tuple[str, ...],
    transform,
    name: str,
    file_name: str,
    note: str,
    require_hex_like: bool = False,
    require_lowercase_change: bool = False,
) -> MutationResult:
    path = find_path_by_exact_names(
        receipt,
        HASH_EXACT_NAMES,
        value_predicate=lambda value: isinstance(value, str)
        and (not require_hex_like or bool(HEX_RE.fullmatch(value)))
        and (not require_lowercase_change or value != value.upper()),
    )
    if path is None:
        path = find_string_path(
            receipt,
            hints,
            require_hex_like=require_hex_like,
            require_lowercase_change=require_lowercase_change,
        )
    if path is None:
        raise SystemExit(f"could not find a string field for mutation {name!r}")
    mutated = copy.deepcopy(receipt)
    before = get_in(mutated, path)
    after = transform(before)
    set_in(mutated, path, after)
    return MutationResult(
        name=name,
        file_name=file_name,
        path=_as_jsonable_path(path),
        before=before,
        after=after,
        note=note,
    )


def mutate_remove_required_field(receipt: Any, *, name: str, file_name: str) -> MutationResult:
    path = find_required_field_path(receipt)
    if path is None:
        raise SystemExit("could not find a required field to remove")
    mutated = copy.deepcopy(receipt)
    before = get_in(mutated, path)
    delete_in(mutated, path)
    return MutationResult(
        name=name,
        file_name=file_name,
        path=_as_jsonable_path(path),
        before=before,
        after=None,
        note="removed a required field",
    )


def mutate_add_unknown_field(receipt: Any, *, name: str, file_name: str) -> MutationResult:
    if not isinstance(receipt, dict):
        raise SystemExit("Phase 37 receipt root must be a JSON object")
    mutated = copy.deepcopy(receipt)
    key = UNKNOWN_FIELD_KEY
    suffix = 2
    while key in mutated:
        key = f"{UNKNOWN_FIELD_KEY}_{suffix}"
        suffix += 1
    mutated[key] = {
        "kind": "unexpected",
        "mutation": name,
    }
    return MutationResult(
        name=name,
        file_name=file_name,
        path=[key],
        before=None,
        after=mutated[key],
        note="added an unknown top-level field",
    )


def mutate_total_steps_zero(receipt: Any, *, name: str, file_name: str) -> MutationResult:
    path = find_first_path(
        receipt,
        predicate=lambda _path, key, value: isinstance(key, str)
        and key.lower() == "total_steps"
        and isinstance(value, int),
    )
    if path is None:
        raise SystemExit("could not find total_steps field")
    mutated = copy.deepcopy(receipt)
    before = get_in(mutated, path)
    set_in(mutated, path, 0)
    return MutationResult(
        name=name,
        file_name=file_name,
        path=_as_jsonable_path(path),
        before=before,
        after=0,
        note="set total_steps to zero",
    )


def mutate_source_commitment_drift(
    receipt: Any,
    *,
    name: str,
    file_name: str,
) -> MutationResult:
    source_path = find_path_by_exact_names(
        receipt,
        SOURCE_COMMITMENT_EXACT_NAMES,
        value_predicate=lambda value: isinstance(value, str) and bool(HEX_RE.fullmatch(value)),
    )
    if source_path is None:
        source_path = find_string_path(
            receipt,
            SOURCE_COMMITMENT_KEY_HINTS,
            require_hex_like=True,
            require_lowercase_change=False,
        )
    if source_path is None:
        raise SystemExit("could not find a source commitment field")
    mutated = copy.deepcopy(receipt)
    before = get_in(mutated, source_path)
    after = tamper_hex_string(before)
    set_in(mutated, source_path, after)

    recomputed = False
    recompute_basis_path: list[Any] | None = None
    material_path = find_material_path(mutated)
    final_path = find_path_by_exact_names(
        mutated,
        FINAL_COMMITMENT_EXACT_NAMES,
        value_predicate=lambda value: isinstance(value, str) and bool(HEX_RE.fullmatch(value)),
    )
    if final_path is None:
        final_path = find_string_path(
            mutated,
            FINAL_COMMITMENT_KEY_HINTS,
            require_hex_like=True,
            require_lowercase_change=False,
        )
    if material_path is not None and final_path is not None:
        material = get_in(mutated, material_path)
        digest_hex = hashlib.sha256(canonical_json_bytes(material)).hexdigest()
        template = get_in(mutated, final_path)
        set_in(mutated, final_path, format_digest_like(template, digest_hex))
        recomputed = True
        recompute_basis_path = _as_jsonable_path(material_path)

    return MutationResult(
        name=name,
        file_name=file_name,
        path=_as_jsonable_path(source_path),
        before=before,
        after=after,
        note="drifted a source commitment and recomputed the final commitment when schema-local material was available",
        recomputed_final_commitment=recomputed,
        recompute_basis_path=recompute_basis_path,
    )


def build_mutations(receipt: Any) -> tuple[list[MutationResult], list[dict[str, Any]]]:
    mutation_specs = [
        (
            "flip_false_claim_flag",
            "phase37_bad_01_flip_false_claim_flag.json",
            lambda: mutate_flag(
                receipt,
                desired_value=False,
                hints=FALSE_CLAIM_KEY_HINTS,
                name="flip_false_claim_flag",
                file_name="phase37_bad_01_flip_false_claim_flag.json",
                note="flipped a false claim flag to true",
            ),
        ),
        (
            "flip_true_source_binding_flag",
            "phase37_bad_02_flip_true_source_binding_flag.json",
            lambda: mutate_flag(
                receipt,
                desired_value=True,
                hints=SOURCE_BINDING_KEY_HINTS,
                name="flip_true_source_binding_flag",
                file_name="phase37_bad_02_flip_true_source_binding_flag.json",
                note="flipped a required true source-binding flag to false",
            ),
        ),
        (
            "uppercase_hash",
            "phase37_bad_03_uppercase_hash.json",
            lambda: mutate_string(
                receipt,
                hints=HASH_KEY_HINTS,
                transform=uppercase_hash,
                name="uppercase_hash",
                file_name="phase37_bad_03_uppercase_hash.json",
                note="uppercased a hash-like field",
                require_hex_like=True,
                require_lowercase_change=True,
            ),
        ),
        (
            "remove_required_field",
            "phase37_bad_04_remove_required_field.json",
            lambda: mutate_remove_required_field(
                receipt,
                name="remove_required_field",
                file_name="phase37_bad_04_remove_required_field.json",
            ),
        ),
        (
            "add_unknown_field",
            "phase37_bad_05_add_unknown_field.json",
            lambda: mutate_add_unknown_field(
                receipt,
                name="add_unknown_field",
                file_name="phase37_bad_05_add_unknown_field.json",
            ),
        ),
        (
            "zero_total_steps",
            "phase37_bad_06_zero_total_steps.json",
            lambda: mutate_total_steps_zero(
                receipt,
                name="zero_total_steps",
                file_name="phase37_bad_06_zero_total_steps.json",
            ),
        ),
        (
            "tamper_final_commitment",
            "phase37_bad_07_tamper_final_commitment.json",
            lambda: mutate_string(
                receipt,
                hints=FINAL_COMMITMENT_KEY_HINTS,
                transform=tamper_hex_string,
                name="tamper_final_commitment",
                file_name="phase37_bad_07_tamper_final_commitment.json",
                note="tampered the final commitment without changing the surrounding receipt",
                require_hex_like=True,
            ),
        ),
        (
            "drift_source_commitment",
            "phase37_bad_08_drift_source_commitment.json",
            lambda: mutate_source_commitment_drift(
                receipt,
                name="drift_source_commitment",
                file_name="phase37_bad_08_drift_source_commitment.json",
            ),
        ),
    ]

    results: list[MutationResult] = []
    output_entries: list[dict[str, Any]] = []
    for index, (_name, file_name, builder) in enumerate(mutation_specs, start=1):
        result = builder()
        result_dict = {
            "name": result.name,
            "file_name": result.file_name,
            "path": result.path,
            "before": result.before,
            "after": result.after,
            "note": result.note,
            "recomputed_final_commitment": result.recomputed_final_commitment,
            "recompute_basis_path": result.recompute_basis_path,
            "index": index,
        }
        results.append(result)
        output_entries.append(result_dict)
    return results, output_entries


def generate(receipt_path: pathlib.Path, output_dir: pathlib.Path, manifest_name: str) -> pathlib.Path:
    receipt = load_json(receipt_path)
    if not isinstance(receipt, dict):
        raise SystemExit("Phase 37 receipt must be a JSON object at the root")

    output_dir.mkdir(parents=True, exist_ok=True)

    receipts_mutations, manifest_mutations = build_mutations(receipt)
    for mutation in receipts_mutations:
        mutated = copy.deepcopy(receipt)
        if mutation.name == "flip_false_claim_flag":
            path = find_path_by_exact_names(
                mutated,
                FALSE_CLAIM_EXACT_NAMES,
                value_predicate=lambda value: isinstance(value, bool) and value is False,
            )
            if path is None:
                path = find_bool_path(mutated, False, FALSE_CLAIM_KEY_HINTS)
            assert path is not None
            set_in(mutated, path, True)
        elif mutation.name == "flip_true_source_binding_flag":
            path = find_path_by_exact_names(
                mutated,
                SOURCE_BINDING_EXACT_NAMES,
                value_predicate=lambda value: isinstance(value, bool) and value is True,
            )
            if path is None:
                path = find_bool_path(mutated, True, SOURCE_BINDING_KEY_HINTS)
            assert path is not None
            set_in(mutated, path, False)
        elif mutation.name == "uppercase_hash":
            path = find_path_by_exact_names(
                mutated,
                HASH_EXACT_NAMES,
                value_predicate=lambda value: isinstance(value, str)
                and bool(HEX_RE.fullmatch(value))
                and value != value.upper(),
            )
            if path is None:
                path = find_string_path(
                    mutated,
                    HASH_KEY_HINTS,
                    require_hex_like=True,
                    require_lowercase_change=True,
                )
            assert path is not None
            set_in(mutated, path, uppercase_hash(get_in(mutated, path)))
        elif mutation.name == "remove_required_field":
            path = find_required_field_path(mutated)
            assert path is not None
            delete_in(mutated, path)
        elif mutation.name == "add_unknown_field":
            key = UNKNOWN_FIELD_KEY
            suffix = 2
            while key in mutated:
                key = f"{UNKNOWN_FIELD_KEY}_{suffix}"
                suffix += 1
            mutated[key] = {"kind": "unexpected", "mutation": mutation.name}
        elif mutation.name == "zero_total_steps":
            path = find_first_path(
                mutated,
                predicate=lambda _path, key, value: isinstance(key, str)
                and key.lower() == "total_steps"
                and isinstance(value, int),
            )
            assert path is not None
            set_in(mutated, path, 0)
        elif mutation.name == "tamper_final_commitment":
            path = find_path_by_exact_names(
                mutated,
                FINAL_COMMITMENT_EXACT_NAMES,
                value_predicate=lambda value: isinstance(value, str)
                and bool(HEX_RE.fullmatch(value)),
            )
            if path is None:
                path = find_string_path(mutated, FINAL_COMMITMENT_KEY_HINTS, require_hex_like=True)
            assert path is not None
            set_in(mutated, path, tamper_hex_string(get_in(mutated, path)))
        elif mutation.name == "drift_source_commitment":
            source_path = find_path_by_exact_names(
                mutated,
                SOURCE_COMMITMENT_EXACT_NAMES,
                value_predicate=lambda value: isinstance(value, str)
                and bool(HEX_RE.fullmatch(value)),
            )
            if source_path is None:
                source_path = find_string_path(
                    mutated, SOURCE_COMMITMENT_KEY_HINTS, require_hex_like=True
                )
            assert source_path is not None
            set_in(mutated, source_path, tamper_hex_string(get_in(mutated, source_path)))
            material_path = find_material_path(mutated)
            final_path = find_path_by_exact_names(
                mutated,
                FINAL_COMMITMENT_EXACT_NAMES,
                value_predicate=lambda value: isinstance(value, str)
                and bool(HEX_RE.fullmatch(value)),
            )
            if final_path is None:
                final_path = find_string_path(
                    mutated, FINAL_COMMITMENT_KEY_HINTS, require_hex_like=True
                )
            if material_path is not None and final_path is not None:
                material = get_in(mutated, material_path)
                digest_hex = hashlib.sha256(canonical_json_bytes(material)).hexdigest()
                template = get_in(mutated, final_path)
                set_in(mutated, final_path, format_digest_like(template, digest_hex))
        else:
            raise AssertionError(f"unexpected mutation {mutation.name!r}")

        dump_json(output_dir / mutation.file_name, mutated)

    manifest = {
        "schema": "phase37-bad-artifact-manifest-v1",
        "source_receipt": {
            "path": str(receipt_path.resolve()),
            "sha256": sha256_file(receipt_path),
        },
        "output_dir": str(output_dir.resolve()),
        "mutation_count": len(manifest_mutations),
        "mutations": manifest_mutations,
    }
    manifest_path = output_dir / manifest_name
    dump_json(manifest_path, manifest)
    return manifest_path


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic adversarial mutations for a Phase 37 receipt JSON"
    )
    parser.add_argument("receipt_json", type=pathlib.Path, help="path to a valid Phase 37 receipt JSON")
    parser.add_argument("output_dir", type=pathlib.Path, help="directory to write mutated artifacts to")
    parser.add_argument(
        "--manifest-name",
        default=MANIFEST_NAME,
        help=f"manifest file name inside the output directory (default: {MANIFEST_NAME})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    manifest_path = generate(args.receipt_json, args.output_dir, args.manifest_name)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
