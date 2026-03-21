"""Parse wasm-bindgen _bg.js glue code to extract boundary functions."""

import re
from dataclasses import dataclass, field


@dataclass
class BoundaryParam:
    name: str
    inferred_type: str  # "i32", "f32", "string", "bytes", "jsvalue", "jsvalue_array", "unknown"
    cost_markers: list[str] = field(default_factory=list)


@dataclass
class BoundaryFunction:
    name: str
    kind: str  # "export" or "import"
    params: list[BoundaryParam] = field(default_factory=list)
    return_type: str = "void"  # "i32", "string", "bytes", "jsvalue", "void"
    body: str = ""
    line_number: int = 0


# Patterns that indicate specific type serialization in function bodies
COST_PATTERNS = {
    "passStringToWasm": "string",
    "getStringFromWasm": "string",
    "passArray8ToWasm": "bytes",
    "passArray16ToWasm": "bytes",
    "passArray32ToWasm": "bytes",
    "passArrayF32ToWasm": "bytes",
    "passArrayF64ToWasm": "bytes",
    "getArrayU8FromWasm": "bytes",
    "getArrayI8FromWasm": "bytes",
    "getArrayU16FromWasm": "bytes",
    "getArrayU32FromWasm": "bytes",
    "getArrayF32FromWasm": "bytes",
    "getArrayF64FromWasm": "bytes",
    "passArrayJsValueToWasm": "jsvalue_array",
    "addHeapObject": "jsvalue",
    "takeObject": "jsvalue",
    "getObject": "jsvalue",
}

# wasm-bindgen internal functions to skip
INTERNAL_FUNCS = {
    "__wbg_set_wasm", "addHeapObject", "getObject", "dropObject",
    "takeObject", "getStringFromWasm0", "passStringToWasm0",
    "getUint8ArrayMemory0", "getDataViewMemory0", "passArray8ToWasm0",
    "getArrayU8FromWasm0", "passArrayJsValueToWasm0",
}


def parse_glue_code(source: str) -> list[BoundaryFunction]:
    """Parse _bg.js glue code and extract boundary functions."""
    functions: list[BoundaryFunction] = []

    # Find all export function declarations
    export_pattern = re.compile(
        r'^export\s+function\s+(\w+)\s*\(([^)]*)\)\s*\{',
        re.MULTILINE,
    )

    for match in export_pattern.finditer(source):
        name = match.group(1)
        if name in INTERNAL_FUNCS or name.startswith("__wbg_set_"):
            continue

        param_str = match.group(2).strip()
        body = _extract_body(source, match.end() - 1)
        line_number = source[:match.start()].count('\n') + 1

        is_import = name.startswith("__wbg_") or name.startswith("__wbindgen_")
        kind = "import" if is_import else "export"

        params = _infer_params(param_str, body, is_import=is_import)
        return_type = _infer_return_type(body, is_import=is_import)

        functions.append(BoundaryFunction(
            name=name,
            kind=kind,
            params=params,
            return_type=return_type,
            body=body,
            line_number=line_number,
        ))

    return functions


def _extract_body(source: str, brace_pos: int) -> str:
    """Extract function body from opening brace position."""
    depth = 0
    start = brace_pos
    for i in range(brace_pos, len(source)):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    return source[start:]


def _infer_params(param_str: str, body: str, is_import: bool = False) -> list[BoundaryParam]:
    """Infer parameter types from how they're used in the function body."""
    if not param_str:
        return []

    params = []
    param_names = [p.strip() for p in param_str.split(',') if p.strip()]

    # For import functions, detect ptr+len pairs used with getStringFromWasm0/getArrayFromWasm0
    # Maps param index → ("string_ptr"|"string_len"|"bytes_ptr"|"bytes_len", marker)
    pair_info: dict[int, tuple[str, str]] = {}
    if is_import:
        for i in range(len(param_names) - 1):
            p1, p2 = param_names[i], param_names[i + 1]
            if re.search(rf'getStringFromWasm0\(\s*{re.escape(p1)}\s*,\s*{re.escape(p2)}\s*\)', body):
                pair_info[i] = ("string_ptr", "getStringFromWasm0")
                pair_info[i + 1] = ("string_len", "getStringFromWasm0")
            elif re.search(rf'getArray\w+FromWasm0\(\s*{re.escape(p1)}\s*,\s*{re.escape(p2)}\s*\)', body):
                pair_info[i] = ("bytes_ptr", "getArrayFromWasm0")
                pair_info[i + 1] = ("bytes_len", "getArrayFromWasm0")

    for idx, pname in enumerate(param_names):
        inferred = "i32"  # default: raw numeric
        markers: list[str] = []

        if idx in pair_info:
            inferred, marker = pair_info[idx]
            markers.append(marker)

        # Check if this param is passed to a serialization function (export style)
        elif re.search(rf'passStringToWasm\w*\(\s*{re.escape(pname)}\b', body):
            inferred = "string"
            markers.append("passStringToWasm")
        elif re.search(rf'passArray8ToWasm\w*\(\s*{re.escape(pname)}\b', body):
            inferred = "bytes"
            markers.append("passArray8ToWasm")
        elif re.search(rf'passArrayJsValueToWasm\w*\(\s*{re.escape(pname)}\b', body):
            inferred = "jsvalue_array"
            markers.append("passArrayJsValueToWasm")
        elif re.search(rf'addHeapObject\(\s*{re.escape(pname)}\s*\)', body):
            inferred = "jsvalue"
            markers.append("addHeapObject")
        elif re.search(rf'getObject\(\s*{re.escape(pname)}\s*\)', body):
            inferred = "jsvalue"
            markers.append("getObject")

        params.append(BoundaryParam(name=pname, inferred_type=inferred, cost_markers=markers))

    return params


def _infer_return_type(body: str, is_import: bool = False) -> str:
    """Infer return type from how the return value is constructed."""
    if is_import:
        # For import functions, getStringFromWasm0 in body is for DECODING params,
        # not for constructing the return value. Check actual return statements.
        if re.search(r'return\s+addHeapObject\(', body):
            return "jsvalue"
        if "return ret" in body or "return ret >>>" in body:
            return "i32"
        if "return" not in body:
            return "void"
        return "i32"

    # Export functions
    if re.search(r'return\s+getStringFromWasm0\(', body):
        return "string"
    if "getStringFromWasm0" in body and "deferred" in body and "return" in body:
        # Pattern: deferred free + return getStringFromWasm0
        return "string"
    if "getArrayU8FromWasm0" in body or "getArrayI8FromWasm0" in body:
        return "bytes"
    if re.search(r'getArray\w+FromWasm0', body):
        return "bytes"
    if "takeObject" in body and "return" in body:
        return "jsvalue"
    if "addHeapObject" in body and "return" in body:
        return "jsvalue"
    if "return ret" in body or "return ret >>>" in body:
        return "i32"
    if "return" not in body:
        return "void"
    return "i32"
