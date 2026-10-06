import importlib.util
from pathlib import Path
import struct
import json
import tempfile
import importlib.util
import unittest

P = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts/dart_aot_pool_xrefs.py'
spec = importlib.util.spec_from_file_location('pool_xrefs', P)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def ldr(base, offset, destination=2):
    return 0xf9400000 | ((offset//8) << 10) | (base << 5) | destination


def add(destination, source=27, immediate=0x16, shift=True):
    return 0x91000000 | (int(shift) << 22) | (immediate << 10) | (source << 5) | destination


class PoolXrefsTests(unittest.TestCase):
    def test_patterns_and_counterexamples(self):
        self.assertEqual(m.pool_load(ldr(27, 0x108)), (0x108, 'ldr-pool'))
        self.assertEqual(m.pool_load(ldr(2, 0x788), add(2)), (0x16788, 'adjacent-add-ldr-pool'))
        self.assertEqual(m.pool_load(ldr(2, 0x18), add(2, immediate=0x100, shift=False)), (0x118, 'adjacent-add-ldr-pool'))
        for previous in (None, add(3), add(2, source=26), 0xd503201f):
            self.assertIsNone(m.pool_load(ldr(2, 0x788), previous))
        self.assertIsNone(m.pool_load(ldr(27, 0x108, destination=31)))
        self.assertIsNone(m.pool_load(0xb9400362))  # 32-bit LDR is a different pattern.
        data = struct.pack('<IIII', add(2), 0xd503201f, ldr(2, 0x788), ldr(27, 0x108))
        rows=m.scan(data, 0x1000, {0x16788, 0x108})
        self.assertEqual([r['instruction'] for r in rows], ['0x100c'])
        self.assertEqual(m.scan(struct.pack('<I', ldr(2, 0x788)), 0x2000, {0x16788}), [])

    def test_independent_llvm_instruction_vectors(self):
        # Assembled by Xcode LLVM clang, checked with llvm-objdump; these
        # literals deliberately do not use the local encoding helpers.
        # ldr x2,[x27,#0x108]; add x2,x27,#0x16,lsl #12;
        # ldr x2,[x2,#0x788]; adds/sub x2,x27,#0x16,lsl #12.
        self.assertEqual(m.pool_load(0xf9408762), (0x108, 'ldr-pool'))
        self.assertEqual(m.pool_load(0xf943c442, 0x91405b62),
                         (0x16788, 'adjacent-add-ldr-pool'))
        self.assertIsNone(m.pool_load(0xf943c442, 0xb1405b62))
        self.assertIsNone(m.pool_load(0xf943c442, 0xd1405b62))

    def test_bad_ranges_are_not_silently_scanned(self):
        for value in ([], [{'start':0,'end':3}], [{'start':4,'end':4}],
                      [{'start':0,'end':8},{'start':4,'end':12}],
                      [{'start':False,'end':8}], [{'start':0,'end':8,'guess':True}]):
            with self.assertRaises(ValueError): m.ranges_from_json(value)
        self.assertEqual(m.ranges_from_json([{'start':'0x10','end':'0x18'},{'start':0,'end':8}]),[(0,8),(16,24)])

    @unittest.skipUnless(importlib.util.find_spec('elftools'), 'optional pyelftools dependency')
    def test_file_backing_and_executable_boundary(self):
        def binary(flags=5, machine=183, file_length=8):
            ident=b'\x7fELF'+bytes([2,1,1])+b'\0'*9
            header=struct.pack('<16sHHIQQQIHHHHHH',ident,3,machine,1,0,64,0,0,64,56,1,0,0,0)
            segment=struct.pack('<IIQQQQQQ',1,flags,0x100,0x1000,0x1000,file_length,16,0x1000)
            return header+segment+b'\0'*(0x100-len(header)-len(segment))+struct.pack('<II',add(2),ldr(2,0x788))
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);elf=root/'test.so';ranges=root/'ranges.json';pool=root/'pp.txt'
            ranges.write_text(json.dumps([{'start':0x1000,'end':0x1008}]))
            pool.write_text('[pp+0x16788] String: "fixture-field"\n')
            elf.write_bytes(binary())
            result=m.analyze(elf,ranges,pool,{0x16788})
            self.assertEqual(result['references'][0]['label'],'String: "fixture-field"')
            for data in (binary(flags=4),binary(machine=62),binary(file_length=4)):
                elf.write_bytes(data)
                with self.assertRaises(ValueError):m.analyze(elf,ranges,pool,{0x16788})

if __name__=='__main__': unittest.main()
