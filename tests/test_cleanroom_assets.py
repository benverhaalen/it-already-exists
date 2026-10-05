"""Synthetic reviewed-asset transport checks; no Docker/model/reference trial."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
import assets
import cleanroom
import offline_worker as worker
import workflow


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.data = b'\x89PNG\r\n\x1a\nsynthetic header only'
        (self.root / 'logo.png').write_bytes(self.data)
        self.manifest = dict(scope='fixture', reviewer='fixture reviewer', rights='Owned synthetic bytes permitted', limits='Header-only fixture; no semantic certification',
                             files=[dict(path='logo.png', sha256=hashlib.sha256(self.data).hexdigest(), kind='image')])
        self.spec = dict(scope='fixture', goal='Fixture', audience='fixture', journey={k:'fixture' for k in ('entry','default','action','outcome','reset')}, behaviors=['fixture'], unknowns=[], acceptance=['fixture'], review=dict(reviewer='fixture', implementation_independent=True, source_free=True, asset_rights=True, limits='fixture'))

    def test_snapshot_identity_and_rejections(self):
        self.assertEqual(assets.snapshot(self.manifest, self.root, 'fixture'), {'logo.png': self.data})
        for mutate, reason in [(lambda m: m.update(scope='other'), 'scope'),
                               (lambda m: m['files'][0].update(path='../logo.png'), 'path'),
                               (lambda m: m['files'][0].update(path='code.py'), 'source or archives'),
                               (lambda m: m['files'][0].update(sha256='0'*64), 'hash')]:
            m = json.loads(json.dumps(self.manifest)); mutate(m)
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason): assets.snapshot(m, self.root, 'fixture')
        (self.root / 'logo.png').unlink(); (self.root / 'logo.png').symlink_to(self.root / 'outside')
        with self.assertRaises(OSError): assets.snapshot(self.manifest, self.root, 'fixture')

    def test_renamed_source_and_ancestor_symlink_are_rejected(self):
        data = b'print("source")'; (self.root / 'logo.png').write_bytes(data)
        self.manifest['files'][0]['sha256'] = hashlib.sha256(data).hexdigest()
        with self.assertRaisesRegex(ValueError, 'header'): assets.snapshot(self.manifest, self.root, 'fixture')
        alias = self.root / 'alias'; alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError): assets.snapshot(self.manifest, alias, 'fixture')

    def test_worker_selects_whole_asset_into_delivered_paths_and_limits(self):
        spec = self.root / 'spec.json'; spec.write_text(json.dumps(self.spec))
        model = self.root / 'weights'; model.write_bytes(b'not model')
        output = self.root / 'output'; output.mkdir()
        response = {'files':[{'path':'main.txt','content':'assets/logo.png'}], 'selected_assets':['logo.png']}
        backend = [sys.executable, '-c', 'import json;print('+repr(json.dumps(response))+')', '{prompt}', '{model}']
        receipt = worker.execute(spec, output, model, backend, asset_manifest=self.manifest, asset_root=self.root)
        self.assertEqual((output / 'assets/logo.png').read_bytes(), self.data)
        self.assertEqual(receipt['selected_assets'], assets.inventory({'logo.png':self.data}))
        other = self.root / 'other'; other.mkdir()
        with self.assertRaisesRegex(ValueError, 'output limits'):
            worker.execute(spec, other, model, backend, max_bytes=20, asset_manifest=self.manifest, asset_root=self.root)
        self.assertEqual(list(other.iterdir()), [])

    def test_worker_unapproved_asset_or_generated_asset_namespace_rejected(self):
        spec = self.root / 'spec.json'; spec.write_text(json.dumps(self.spec))
        model = self.root / 'weights'; model.write_bytes(b'not model')
        output = self.root / 'output'; output.mkdir()
        for response in [{'files':[{'path':'main.txt','content':'x'}], 'selected_assets':['unreviewed.png']},
                         {'files':[{'path':'assets/logo.png','content':'forged'}], 'selected_assets':[]}]:
            backend = [sys.executable, '-c', 'print('+repr(json.dumps(response))+')', '{prompt}', '{model}']
            with self.assertRaises(ValueError): worker.execute(spec, output, model, backend, asset_manifest=self.manifest, asset_root=self.root)
            self.assertEqual(list(output.iterdir()), [])

    def test_boundary_uses_only_snapshot_readonly_mount_and_receipt_identity(self):
        observed = []
        def fake_invoke(argv, timeout=120):
            observed.append(argv)
            if argv[0] == 'run':
                mounts = [argv[i+1] for i,a in enumerate(argv) if a == '--mount']
                output = Path(next(m.split(',')[1][4:] for m in mounts if 'dst=/work' in m))
                asset = next(m for m in mounts if 'dst=/assets' in m)
                self.assertTrue(asset.endswith(',readonly'))
                self.assertNotIn('src='+str(self.root)+',', asset)
                if argv[argv.index('sha256:'+'a'*64)+1] == 'node': (output / 'allowed.txt').write_text('fixture')
                else: (output / 'main.txt').write_text('fixture')
            return subprocess.CompletedProcess(argv, 0, '', '')
        with patch.object(cleanroom, 'image_id'), patch.object(cleanroom, 'invoke', fake_invoke):
            receipt = cleanroom.execute('sha256:'+'a'*64, self.spec, ['worker'], 30, self.root / 'delivered', asset_manifest=self.manifest, asset_root=self.root)
        self.assertEqual(receipt['asset_manifest_sha256'], assets.identity(self.manifest))
        self.assertEqual(receipt['asset_inventory'], assets.inventory({'logo.png':self.data}))

    def test_access_review_detects_manifest_or_original_byte_drift(self):
        output = self.root / 'delivered'; output.mkdir(); (output / 'main.txt').write_text('fixture')
        image = 'sha256:'+'a'*64
        receipt = dict(image=image, specification_sha256=hashlib.sha256(json.dumps(self.spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), boundary_probes_passed=True, worker_executed=True, worker_exit=0, output_directory=str(output), output_inventory=[{'path':'main.txt','sha256':hashlib.sha256(b'fixture').hexdigest()}], asset_manifest_sha256=assets.identity(self.manifest), asset_scope='fixture', asset_inventory=assets.inventory({'logo.png':self.data}))
        records=[]
        for name, value in [('spec',self.spec),('receipt',receipt),('assets',self.manifest)]:
            path=self.root/(name+'.json'); path.write_text(json.dumps(value))
            records.append(dict(id=name,kind='evidence',data=dict(basis='observed',local_path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),links=[])))
        review=dict(reviewed=True,reviewer='fixture',declaration='fixture',limits='fixture')
        task={k:self.spec[k] for k in ('scope','goal','audience','journey')}; task.update(access='strict-clean-room',clean_room=dict(specification_evidence='spec',receipt_evidence='receipt',assets_evidence='assets',assets_root=str(self.root),image_review={**review,'image':image},worker_review=review,output_directory=str(output)))
        self.assertTrue(workflow.access_review(task, records, self.root/'journal')['ready'])
        (self.root/'logo.png').write_bytes(self.data+b'changed')
        result=workflow.access_review(task, records, self.root/'journal')
        self.assertFalse(result['ready']); self.assertTrue(any('asset review' in gap for gap in result['gaps']))
        (self.root/'logo.png').write_bytes(self.data); (self.root/'assets.json').write_text('{}')
        self.assertFalse(workflow.access_review(task, records, self.root/'journal')['ready'])

if __name__ == '__main__': unittest.main()
