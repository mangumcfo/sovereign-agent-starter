"""Sovereign Workload Execution — a bounded i32 WASM sandbox that isolates a workload, composing the
sealed parser rather than trusting it to run.

Node-runtime module (S7, KM Seal 1176-INFINITY-RHO 2026-08-06). The sealed P5 `wasm_runtime.WasmModule`
parses a module's section framing but does not execute it (`execute_function` is a `return 0` stub). This
module COMPOSES that sealed parser (for the magic-number check + section framing) and adds the execution
layer the sealed parser never had: a Code-section decoder, an operand stack, locals, a deterministic i32
opcode subset, structured control flow, a call mechanism, and — the point of a *shield* — a trap on any
invalid operation, a fuel bound so a workload cannot hang the node, deny-by-default host imports, and a
bounded linear memory it cannot escape. The sealed bytes under `primitives/sealed/` are never mutated;
this is a node capability laid over the sealed parser, not an overlay or a re-seal.

`WasmSandbox(bytecode).invoke(name, args)` runs an exported function deterministically to a result, or
raises `WasmTrap` — invalid opcode, stack underflow, division by zero, out-of-bounds memory, call-depth
or fuel exhaustion, or a call to a host import the operator did not allow-list. No host escape: the only
host functions a module may call are those explicitly passed in `host_imports`; memory is a private
`bytearray` bounded to the module's declared pages; and every step consumes fuel."""
from __future__ import annotations

from typing import Callable, Dict, List, Mapping, Optional, Sequence

from .._lazy_bp import WasmModule  # sealed P5 parser via the runtime boundary (composed, never mutated)

_U32 = 0xFFFFFFFF
_I32_MIN = -0x80000000


class WasmTrap(Exception):
    """A workload trapped — an invalid opcode, stack underflow, division by zero, out-of-bounds memory,
    call-depth or fuel exhaustion, or a call to a host import the operator did not allow-list. A trap is
    fail-closed: the node is unharmed, the host state untouched, and no partial result is returned."""


def _s32(v: int) -> int:
    v &= _U32
    return v - (1 << 32) if v & 0x80000000 else v


class _Reader:
    """LEB128 + byte reader over a bytes slice."""
    __slots__ = ("b", "pos", "end")

    def __init__(self, b: bytes, pos: int = 0, end: Optional[int] = None):
        self.b, self.pos, self.end = b, pos, (len(b) if end is None else end)

    def byte(self) -> int:
        if self.pos >= self.end:
            raise WasmTrap("unexpected end of code")
        v = self.b[self.pos]
        self.pos += 1
        return v

    def u32(self) -> int:
        result = shift = 0
        while True:
            byte = self.byte()
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                return result
            shift += 7

    def s32(self) -> int:
        result = shift = 0
        while True:
            byte = self.byte()
            result |= (byte & 0x7F) << shift
            shift += 7
            if not (byte & 0x80):
                if byte & 0x40:
                    result |= -(1 << shift)
                return result


class _Func:
    __slots__ = ("type_idx", "n_params", "n_results", "n_locals", "code", "jumps")

    def __init__(self, type_idx, n_params, n_results, n_locals, code, jumps):
        self.type_idx, self.n_params, self.n_results = type_idx, n_params, n_results
        self.n_locals, self.code, self.jumps = n_locals, code, jumps


class WasmSandbox:
    """A bounded i32 WASM sandbox. Composes the sealed parser; adds execution with trap + fuel +
    deny-by-default host + bounded memory."""

    MAX_DEPTH = 256

    def __init__(self, bytecode: bytes, *, fuel: int = 1_000_000, memory_pages: int = 1,
                 host_imports: Optional[Mapping[str, Callable]] = None):
        self.bytecode = bytes(bytecode)
        # Compose the sealed parser as the parser floor (its section-framing model + magic contract).
        # The sealed parser's own section parsing is shallow -- it drops type signatures and never reads
        # the Code section (which is why it is honestly "parser-only") -- so the sandbox re-parses the
        # sections it needs correctly and adds the execution layer the sealed parser never had.
        self._sealed = WasmModule(self.bytecode)
        self.fuel = int(fuel)
        self.memory = bytearray(max(1, int(memory_pages)) * 65536)
        self.host_imports: Dict[str, Callable] = dict(host_imports or {})  # deny-by-default allow-list
        self.types: List[tuple] = []          # [(n_params, n_results)]
        self.import_names: List[str] = []      # imported function field names, in index order
        self.import_type_idx: List[int] = []   # type index per imported function
        self.func_type_idx: List[int] = []     # type index per *defined* function
        self.exports: Dict[str, int] = {}      # export name -> function index (incl. imports offset)
        self.funcs: List[Optional[_Func]] = []
        self._parse()

    # -- section parsing (adds what the sealed parser drops: signatures + the Code section) ----------
    def _parse(self) -> None:
        b = self.bytecode
        if b[:4] != b"\x00asm":
            raise WasmTrap("invalid WebAssembly magic number")
        r = _Reader(b, 8)
        code_bodies: List[tuple] = []
        while r.pos < len(b):
            sec_id = r.u32()
            size = r.u32()
            start = r.pos
            end = start + size
            if sec_id == 1:   # Type
                self._parse_types(_Reader(b, start, end))
            elif sec_id == 2:  # Import
                self._parse_imports(_Reader(b, start, end))
            elif sec_id == 3:  # Function
                fr = _Reader(b, start, end)
                for _ in range(fr.u32()):
                    self.func_type_idx.append(fr.u32())
            elif sec_id == 7:  # Export
                self._parse_exports(_Reader(b, start, end))
            elif sec_id == 10:  # Code
                cr = _Reader(b, start, end)
                for _ in range(cr.u32()):
                    body_size = cr.u32()
                    body_end = cr.pos + body_size
                    code_bodies.append((cr.pos, body_end))
                    cr.pos = body_end
            r.pos = end
        n_imports = len(self.import_names)
        if len(code_bodies) != len(self.func_type_idx):
            raise WasmTrap("function/code section count mismatch")
        for i, (bstart, bend) in enumerate(code_bodies):
            tidx = self.func_type_idx[i]
            n_params, n_results = self.types[tidx] if tidx < len(self.types) else (0, 0)
            self.funcs.append(self._parse_body(bstart, bend, tidx, n_params, n_results))
        # index space: [imports...][defined funcs...]
        self.funcs = [None] * n_imports + self.funcs

    def _parse_types(self, r: _Reader) -> None:
        for _ in range(r.u32()):
            if r.byte() != 0x60:
                raise WasmTrap("invalid function type form")
            n_params = r.u32()
            for _ in range(n_params):
                r.byte()  # valtype
            n_results = r.u32()
            for _ in range(n_results):
                r.byte()
            self.types.append((n_params, n_results))

    def _parse_imports(self, r: _Reader) -> None:
        for _ in range(r.u32()):
            mlen = r.u32(); r.pos += mlen                       # module name (unused)
            flen = r.u32()
            field = self.bytecode[r.pos:r.pos + flen].decode("utf-8", "replace"); r.pos += flen
            kind = r.byte()
            if kind == 0x00:  # function import
                self.import_type_idx.append(r.u32())  # type idx
                self.import_names.append(field)
            elif kind in (0x01, 0x02, 0x03):
                r.u32(); r.byte()  # table/mem/global descriptors (coarsely skipped)

    def _parse_exports(self, r: _Reader) -> None:
        for _ in range(r.u32()):
            nlen = r.u32()
            name = self.bytecode[r.pos:r.pos + nlen].decode("utf-8", "replace"); r.pos += nlen
            kind = r.byte()
            idx = r.u32()
            if kind == 0x00:  # function export
                self.exports[name] = idx

    def _parse_body(self, start: int, end: int, tidx: int, n_params: int, n_results: int) -> _Func:
        r = _Reader(self.bytecode, start, end)
        n_locals = 0
        for _ in range(r.u32()):  # local declaration groups
            count = r.u32()
            r.byte()  # valtype
            n_locals += count
        code = self.bytecode[r.pos:end]
        jumps = self._scan_jumps(code)
        return _Func(tidx, n_params, n_results, n_locals, code, jumps)

    # -- pre-scan structured control flow: match block/loop/if <-> else <-> end ----------------------
    def _scan_jumps(self, code: bytes) -> Dict[int, dict]:
        jumps: Dict[int, dict] = {}
        stack: List[int] = []
        r = _Reader(code)
        while r.pos < len(code):
            op_pc = r.pos
            op = r.byte()
            if op in (0x02, 0x03, 0x04):          # block / loop / if
                r.byte()                           # blocktype
                jumps[op_pc] = {"op": op, "else": None, "end": None}
                stack.append(op_pc)
            elif op == 0x05:                       # else
                if stack:
                    jumps[stack[-1]]["else"] = op_pc
            elif op == 0x0B:                       # end
                if stack:
                    jumps[stack.pop()]["end"] = op_pc
            elif op in (0x0C, 0x0D, 0x10):         # br / br_if / call (one leb operand)
                r.u32()
            elif op == 0x41:                       # i32.const
                r.s32()
            elif op in (0x20, 0x21, 0x22):         # local.get/set/tee
                r.u32()
            elif op in (0x28, 0x36):               # i32.load / i32.store (align, offset)
                r.u32(); r.u32()
            elif op in (0x3F, 0x40):               # memory.size / memory.grow
                r.byte()
            # all other opcodes are single-byte
        return jumps

    # -- execution ----------------------------------------------------------------------------------
    def invoke(self, name: str, args: Sequence[int] = ()) -> Optional[int]:
        if name not in self.exports:
            raise WasmTrap(f"no exported function {name!r}")
        fidx = self.exports[name]
        return self._call(fidx, [(_s32(a) & _U32) for a in args], depth=0)

    def _burn(self, n: int = 1) -> None:
        self.fuel -= n
        if self.fuel < 0:
            raise WasmTrap("out of fuel (workload exceeded its step bound)")

    def _call(self, fidx: int, args: List[int], depth: int) -> Optional[int]:
        if depth > self.MAX_DEPTH:
            raise WasmTrap("call depth exceeded")
        if fidx < 0 or fidx >= len(self.funcs):
            raise WasmTrap(f"call to undefined function index {fidx}")
        fn = self.funcs[fidx]
        if fn is None:  # an imported function: deny-by-default host boundary
            fname = self.import_names[fidx] if fidx < len(self.import_names) else f"import#{fidx}"
            host = self.host_imports.get(fname)
            if host is None:
                raise WasmTrap(f"host import {fname!r} is not allow-listed (deny-by-default host)")
            self._burn()
            return _s32(int(host(*[_s32(a) for a in args]))) & _U32
        locals_ = list(args[:fn.n_params]) + [0] * (fn.n_params - len(args)) + [0] * fn.n_locals
        return self._run(fn, locals_, depth)

    def _run(self, fn: _Func, locals_: List[int], depth: int) -> Optional[int]:
        code, jumps = fn.code, fn.jumps
        stack: List[int] = []
        ctrl: List[dict] = []  # control frames: {is_loop, header, end}
        r = _Reader(code)

        def pop() -> int:
            if not stack:
                raise WasmTrap("operand stack underflow")
            return stack.pop()

        while r.pos < len(code):
            self._burn()
            op = r.byte()
            if op == 0x0F:                                   # return
                break
            elif op == 0x0B:                                 # end
                if ctrl:
                    ctrl.pop()
                else:
                    break                                     # end of function body
            elif op == 0x00:                                 # unreachable
                raise WasmTrap("unreachable")
            elif op == 0x01:                                 # nop
                pass
            elif op == 0x02 or op == 0x03:                   # block / loop
                r.byte()
                info = jumps[r.pos - 2]
                ctrl.append({"is_loop": op == 0x03, "header": r.pos, "end": info["end"]})
            elif op == 0x04:                                 # if
                r.byte()
                info = jumps[r.pos - 2]
                cond = _s32(pop())
                ctrl.append({"is_loop": False, "header": r.pos, "end": info["end"]})
                if cond == 0:
                    # skip the then-branch: jump to the else-body, or to the `end` opcode (which pops
                    # the if-frame). Either way the `end`/else path pops the frame exactly once.
                    r.pos = (info["else"] + 1) if info["else"] is not None else info["end"]
            elif op == 0x05:                                 # else (reached at end of then-branch)
                frame = ctrl[-1] if ctrl else None
                r.pos = frame["end"] if frame else len(code)  # skip the else-branch
            elif op == 0x0C or op == 0x0D:                   # br / br_if
                label = r.u32()
                do = True
                if op == 0x0D:
                    do = _s32(pop()) != 0
                if do:
                    if label >= len(ctrl):
                        break                                 # branch out of the function == return
                    target = ctrl[-(label + 1)]
                    del ctrl[len(ctrl) - label - 1:]          # pop label frames (target inclusive)
                    if target["is_loop"]:
                        ctrl.append(target)                    # re-enter the loop (frame stays live)
                        r.pos = target["header"]
                    else:
                        r.pos = target["end"] + 1              # exit PAST the block's end (frame popped)
            elif op == 0x10:                                 # call
                fidx = r.u32()
                callee = self.funcs[fidx] if 0 <= fidx < len(self.funcs) else None
                n_args = (callee.n_params if callee is not None
                          else self.types[self._imp_type(fidx)][0])
                cargs = [pop() for _ in range(n_args)][::-1]
                res = self._call(fidx, cargs, depth + 1)
                if res is not None:
                    stack.append(res & _U32)
            elif op == 0x1A:                                 # drop
                pop()
            elif op == 0x20:                                 # local.get
                stack.append(locals_[r.u32()] & _U32)
            elif op == 0x21:                                 # local.set
                locals_[r.u32()] = pop() & _U32
            elif op == 0x22:                                 # local.tee
                locals_[r.u32()] = stack[-1] & _U32 if stack else self._underflow()
            elif op == 0x41:                                 # i32.const
                stack.append(r.s32() & _U32)
            elif op == 0x45:                                 # i32.eqz
                stack.append(1 if _s32(pop()) == 0 else 0)
            elif 0x46 <= op <= 0x4F:                         # i32 comparisons
                b = pop(); a = pop()
                stack.append(1 if self._cmp(op, a, b) else 0)
            elif 0x6A <= op <= 0x78:                         # i32 arithmetic / bitwise
                b = pop(); a = pop()
                stack.append(self._arith(op, a, b) & _U32)
            elif op == 0x28:                                 # i32.load
                r.u32(); off = r.u32()
                stack.append(self._load(pop() + off))
            elif op == 0x36:                                 # i32.store
                r.u32(); off = r.u32()
                val = pop(); addr = pop()
                self._store(addr + off, val)
            elif op == 0x3F:                                 # memory.size
                r.byte(); stack.append(len(self.memory) // 65536)
            elif op == 0x40:                                 # memory.grow (bounded: refuse to grow)
                r.byte(); pop(); stack.append(_U32)          # -1: growth denied (bounded memory)
            else:
                raise WasmTrap(f"invalid or unsupported opcode 0x{op:02x}")

        if fn.n_results == 0:
            return None
        return _s32(pop()) & _U32

    def _underflow(self):
        raise WasmTrap("operand stack underflow")

    def _imp_type(self, fidx: int) -> int:
        # type index of an imported function (index space: imports come first)
        return self.import_type_idx[fidx] if fidx < len(self.import_type_idx) else 0

    def _cmp(self, op: int, a: int, b: int) -> bool:
        sa, sb, ua, ub = _s32(a), _s32(b), a & _U32, b & _U32
        return {
            0x46: a == b, 0x47: a != b,
            0x48: sa < sb, 0x49: ua < ub, 0x4A: sa > sb, 0x4B: ua > ub,
            0x4C: sa <= sb, 0x4D: ua <= ub, 0x4E: sa >= sb, 0x4F: ua >= ub,
        }[op]

    def _arith(self, op: int, a: int, b: int) -> int:
        sa, sb, ua, ub = _s32(a), _s32(b), a & _U32, b & _U32
        if op == 0x6A: return ua + ub
        if op == 0x6B: return ua - ub
        if op == 0x6C: return ua * ub
        if op in (0x6D, 0x6F):  # div_s / rem_s
            if sb == 0:
                raise WasmTrap("integer divide by zero")
            if op == 0x6D and sa == _I32_MIN and sb == -1:
                raise WasmTrap("integer overflow")
            q = abs(sa) // abs(sb)
            q = -q if (sa < 0) != (sb < 0) else q
            return q if op == 0x6D else sa - q * sb
        if op in (0x6E, 0x70):  # div_u / rem_u
            if ub == 0:
                raise WasmTrap("integer divide by zero")
            return (ua // ub) if op == 0x6E else (ua % ub)
        if op == 0x71: return ua & ub
        if op == 0x72: return ua | ub
        if op == 0x73: return ua ^ ub
        if op == 0x74: return ua << (ub & 31)
        if op == 0x75: return _s32(ua) >> (ub & 31)      # shr_s (arithmetic)
        if op == 0x76: return ua >> (ub & 31)             # shr_u (logical)
        if op == 0x77: return ((ua << (ub & 31)) | (ua >> (32 - (ub & 31) or 32))) & _U32  # rotl
        if op == 0x78: return ((ua >> (ub & 31)) | (ua << (32 - (ub & 31) or 32))) & _U32  # rotr
        raise WasmTrap(f"invalid arithmetic opcode 0x{op:02x}")

    def _load(self, addr: int) -> int:
        addr &= _U32
        if addr + 4 > len(self.memory):
            raise WasmTrap("out-of-bounds memory access (load)")
        return int.from_bytes(self.memory[addr:addr + 4], "little")

    def _store(self, addr: int, val: int) -> None:
        addr &= _U32
        if addr + 4 > len(self.memory):
            raise WasmTrap("out-of-bounds memory access (store)")
        self.memory[addr:addr + 4] = (val & _U32).to_bytes(4, "little")
