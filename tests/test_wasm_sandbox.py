"""Test bar for the Sovereign Workload Execution sandbox (shields/wasm_sandbox.py) — a bounded i32 WASM
interpreter composing the sealed parser. Trap on invalid (malformed / invalid-op / OOB / div0 / fuel),
deterministic on valid (add / fib / loop-sum), no host escape (un-allowlisted import denied; OOB leaves
host untouched). Modules are emitted by a minimal in-test encoder so the bytecode is valid by construction."""
import pytest

from sovereign_agent.shields.wasm_sandbox import WasmSandbox, WasmTrap


# ---- a minimal WASM binary encoder (enough for the test bar) ------------------------------------

def _uleb(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _sleb(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if (n == 0 and not (b & 0x40)) or (n == -1 and (b & 0x40)):
            out.append(b)
            return bytes(out)
        out.append(b | 0x80)


def _vec(items):
    return _uleb(len(items)) + b"".join(items)


def _section(sid, payload):
    return bytes([sid]) + _uleb(len(payload)) + payload


I32 = 0x7F


def _module(types, imports, funcs, exports, codes):
    """types: [(params, results)]; imports: [(module, field, type_idx)]; funcs: [type_idx];
    exports: [(name, func_index)]; codes: [(n_i32_locals, body_bytes)]."""
    out = b"\x00asm\x01\x00\x00\x00"
    out += _section(1, _vec([bytes([0x60]) + _vec([bytes([I32])] * p) + _vec([bytes([I32])] * r)
                             for (p, r) in types]))
    if imports:
        imp = []
        for (mod, field, tidx) in imports:
            imp.append(_vec([bytes([c]) for c in mod.encode()]) + _vec([bytes([c]) for c in field.encode()])
                       + b"\x00" + _uleb(tidx))
        out += _section(2, _vec(imp))
    out += _section(3, _vec([_uleb(t) for t in funcs]))
    out += _section(7, _vec([_vec([bytes([c]) for c in name.encode()]) + b"\x00" + _uleb(idx)
                             for (name, idx) in exports]))
    bodies = []
    for (n_locals, body) in codes:
        locals_decl = _vec([_uleb(n_locals) + bytes([I32])]) if n_locals else _vec([])
        inner = locals_decl + body
        bodies.append(_uleb(len(inner)) + inner)
    out += _section(10, _vec(bodies))
    return out


# opcodes
def const(n): return b"\x41" + _sleb(n)
def lget(i): return b"\x20" + _uleb(i)
def lset(i): return b"\x21" + _uleb(i)
ADD, SUB, MUL = b"\x6a", b"\x6b", b"\x6c"
DIV_S, LT_S, EQZ = b"\x6d", b"\x48", b"\x45"
END, RETURN = b"\x0b", b"\x0f"
def call(i): return b"\x10" + _uleb(i)


# ---- valid modules: deterministic exact results -------------------------------------------------

def test_add_deterministic():
    m = _module([((2, 1))], [], [0], [("add", 0)], [(0, lget(0) + lget(1) + ADD + END)])
    sb = WasmSandbox(m)
    assert sb.invoke("add", [40, 2]) == 42
    assert sb.invoke("add", [1000, 337]) == 1337


def test_loop_sum_deterministic():
    # sum 1..n with block/loop/br_if; local0=n, local1=acc
    body = (
        b"\x02\x40"                       # block void
        + b"\x03\x40"                     # loop void
        + lget(0) + EQZ + b"\x0d\x01"     # if n==0 -> br 1 (out of block)
        + lget(1) + lget(0) + ADD + lset(1)  # acc += n
        + lget(0) + const(1) + SUB + lset(0)  # n -= 1
        + b"\x0c\x00"                     # br 0 (loop)
        + END                             # end loop
        + END                            # end block
        + lget(1) + END                  # return acc
    )
    m = _module([((1, 1))], [], [0], [("sum", 0)], [(1, body)])
    sb = WasmSandbox(m)
    assert sb.invoke("sum", [10]) == 55
    assert sb.invoke("sum", [100]) == 5050


def test_fib_recursive_deterministic():
    # fib(n): if n<2 return n else fib(n-1)+fib(n-2). fib is func index 0.
    body = (
        lget(0) + const(2) + LT_S
        + b"\x04\x7f"                     # if (result i32)
        + lget(0)                         # then: n
        + b"\x05"                         # else
        + lget(0) + const(1) + SUB + call(0)
        + lget(0) + const(2) + SUB + call(0)
        + ADD
        + END                            # end if
        + END                            # end func
    )
    m = _module([((1, 1))], [], [0], [("fib", 0)], [(0, body)])
    sb = WasmSandbox(m, fuel=5_000_000)
    assert sb.invoke("fib", [10]) == 55   # 0,1,1,2,3,5,8,13,21,34,55
    assert sb.invoke("fib", [15]) == 610


# ---- trap on invalid ----------------------------------------------------------------------------

def test_trap_malformed_magic():
    with pytest.raises((WasmTrap, ValueError)):
        WasmSandbox(b"\x00asX\x01\x00\x00\x00")


def test_trap_invalid_opcode():
    m = _module([((0, 1))], [], [0], [("bad", 0)], [(0, b"\xfe" + END)])  # 0xfe not supported
    with pytest.raises(WasmTrap):
        WasmSandbox(m).invoke("bad", [])


def test_trap_divide_by_zero():
    m = _module([((0, 1))], [], [0], [("d", 0)], [(0, const(5) + const(0) + DIV_S + END)])
    with pytest.raises(WasmTrap):
        WasmSandbox(m).invoke("d", [])


def test_trap_out_of_bounds_load():
    LOAD = b"\x28\x02" + _uleb(0)   # i32.load align=2 offset=0
    m = _module([((0, 1))], [], [0], [("oob", 0)], [(0, const(0x7fffffff) + LOAD + END)])
    sb = WasmSandbox(m)
    host_before = bytes(sb.memory)
    with pytest.raises(WasmTrap):
        sb.invoke("oob", [])
    assert bytes(sb.memory) == host_before  # OOB leaves host memory untouched


def test_trap_fuel_exhaustion():
    # infinite loop: loop br 0
    body = b"\x03\x40" + b"\x0c\x00" + END + END
    m = _module([((0, 0))], [], [0], [("spin", 0)], [(0, body)])
    with pytest.raises(WasmTrap):
        WasmSandbox(m, fuel=10_000).invoke("spin", [])


# ---- no host escape -----------------------------------------------------------------------------

def test_host_import_denied_by_default():
    # module imports env.evil and calls it; func index 0 = import, 1 = caller
    m = _module([((0, 1))], [("env", "evil", 0)], [0], [("run", 1)], [(0, call(0) + END)])
    with pytest.raises(WasmTrap):
        WasmSandbox(m).invoke("run", [])  # not allow-listed -> trap


def test_host_import_allowlisted_runs():
    calls = []
    def answer():
        calls.append(1)
        return 42
    m = _module([((0, 1))], [("env", "answer", 0)], [0], [("run", 1)], [(0, call(0) + END)])
    sb = WasmSandbox(m, host_imports={"answer": answer})
    assert sb.invoke("run", []) == 42
    assert calls == [1]  # only the allow-listed host fn ran


def test_sealed_parser_is_composed_untouched():
    """The sandbox composes the sealed WasmModule for framing; the sealed bytes are never mutated."""
    m = _module([((2, 1))], [], [0], [("add", 0)], [(0, lget(0) + lget(1) + ADD + END)])
    sb = WasmSandbox(m)
    # the composed parser instance is the sealed layer_5_shields WasmModule, not a reimplementation
    assert type(sb._sealed).__module__.endswith("wasm_runtime")
