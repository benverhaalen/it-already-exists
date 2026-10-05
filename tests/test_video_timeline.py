"""Reviewed visible-transition evidence and stale/ambiguous media failures."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import struct
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/reference-driven-development/scripts'))
import comparison as c
import video_timeline as v

class VideoTimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.video=root/'video.mp4';self.video.write_bytes(b'bound recording')
        self.artifact=root/'app.apk';self.artifact.write_bytes(b'bound application')
        self.timeline=dict(video_sha256=hashlib.sha256(self.video.read_bytes()).hexdigest(),
                           frames=[dict(index=i,pts_seconds=t) for i,t in enumerate([0,.01,.20,.21])])
        self.contract=dict(properties=[dict(id='transition',kind='duration',start='start',observation='done',tolerance=.05)])
        self.selection=dict(fixture='reset',journey='visible response',events=[
            dict(id='start',before_frame=0,after_frame=1,meaning='First observed stimulus indicator'),
            dict(id='done',before_frame=2,after_frame=3,meaning='Count visibly changed')])
        self.review=self.approval()
    def approval(self):
        return dict(approved=True,reviewer='independent observer',timeline_sha256=c.canonical(self.timeline),
            video_sha256=hashlib.sha256(self.video.read_bytes()).hexdigest(),artifact_sha256=hashlib.sha256(self.artifact.read_bytes()).hexdigest(),
            contract_sha256=c.canonical(self.contract),selection_sha256=c.canonical(self.selection))
    def prepare(self):return v.prepare(self.timeline,self.video,self.artifact,self.contract,self.selection,self.review)
    def test_variable_pts_brackets_survive_export_and_detect_response_defect(self):
        reference=self.prepare();candidate=self.prepare()
        self.assertEqual(reference['observations'][1]['time_bounds'],[.2,.21])
        self.assertEqual(c.compare(self.contract,reference,candidate,'.','.')['status'],'passed')
        candidate['observations'][1].update(time=.025,time_bounds=[.02,.03])
        self.assertEqual(c.compare(self.contract,reference,candidate,'.','.')['status'],'failed')
    def test_changed_inputs_and_unreviewed_selection_are_rejected(self):
        self.video.write_bytes(b'different recording')
        with self.assertRaisesRegex(ValueError,'review'):self.prepare()
        self.video.write_bytes(b'bound recording');self.selection['events'][1]['meaning']='A different event'
        with self.assertRaisesRegex(ValueError,'review'):self.prepare()
    def test_probe_cannot_replace_missing_pts_with_inferred_time(self):
        tool=self.video.parent/'ffprobe';tool.write_bytes(b'trusted test executable')
        for frames in ([dict(best_effort_timestamp_time='0'),dict(best_effort_timestamp_time='.1')],
                       [dict(pts_time='0'),dict(pts_time='0')]):
            raw=json.dumps(dict(streams=[dict(width=1080,height=2400)],frames=frames)).encode()
            with self.subTest(frames=frames), patch.object(v,'run',return_value=dict(status='completed',exit_code=0,stdout=raw)):
                with self.assertRaises(ValueError):v.inspect(self.video,tool)

    def test_nonadjacent_and_duplicate_frames_cannot_establish_transition(self):
        self.selection['events'][0]['after_frame']=2;self.review=self.approval()
        with self.assertRaisesRegex(ValueError,'adjacent'):self.prepare()
        self.selection['events'][0]['after_frame']=1
        self.timeline['frames'][1]['pts_seconds']=0;self.review=self.approval()
        with self.assertRaisesRegex(ValueError,'ordered'):self.prepare()

    def extraction_fixture(self):
        self.timeline.update(video_bytes=self.video.stat().st_size,stream=dict(width=2,height=3))
        self.tool=self.video.parent/'decoder';self.tool.write_bytes(b'trusted test executable')
        current=dict(self.timeline,ffprobe_sha256='probe',probe_output_sha256='receipt')
        return current,self.video.parent/'frames'

    def decoder_output(self, argv, root, **kwargs):
        stage=Path(root)/'evidence'
        for i in range(2):
            (stage/('frame-%04d.png'%i)).write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'+struct.pack('>II',2,3)+bytes(9))
        self.assertIn('select=eq(n\\,0)+eq(n\\,2)',argv)
        self.assertIn('passthrough',argv)
        self.assertNotIn('-r',argv)
        return dict(status='completed',exit_code=0)

    def test_frame_evidence_retains_indices_pts_and_hashes_without_overwrite(self):
        current,output=self.extraction_fixture()
        with patch.object(v,'inspect',return_value=current),patch.object(v,'run',side_effect=self.decoder_output):
            result=v.extract(self.timeline,self.video,[0,2],self.tool,self.tool,output)
        self.assertEqual([(f['index'],f['pts_seconds']) for f in result['frames']],[(0,0),(2,.2)])
        for frame in result['frames']:
            self.assertEqual(frame['sha256'],hashlib.sha256((output/frame['file']).read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError,'new'):v.extract(self.timeline,self.video,[0],self.tool,self.tool,output)

    def test_stale_timeline_and_invalid_selection_publish_nothing(self):
        current,output=self.extraction_fixture()
        for indices in ([True],[2,0],[0,0],[4],[]):
            with self.subTest(indices=indices),patch.object(v,'inspect',return_value=current):
                with self.assertRaises(ValueError):v.extract(self.timeline,self.video,indices,self.tool,self.tool,output)
                self.assertFalse(output.exists())
        stale=dict(current,frames=[dict(index=0,pts_seconds=9)])
        with patch.object(v,'inspect',return_value=stale):
            with self.assertRaisesRegex(ValueError,'freshly'):v.extract(self.timeline,self.video,[0],self.tool,self.tool,output)
        self.assertFalse(output.exists())

    def test_dropped_extra_and_wrong_geometry_frames_are_rejected(self):
        current,output=self.extraction_fixture()
        for defect in ('dropped','extra','geometry'):
            def faulty(argv,root,**kwargs):
                result=self.decoder_output(argv,root,**kwargs);stage=Path(root)/'evidence'
                if defect=='dropped':(stage/'frame-0001.png').unlink()
                elif defect=='extra':(stage/'frame-0002.png').write_bytes(b'extra')
                else:(stage/'frame-0001.png').write_bytes(b'wrong geometry')
                return result
            with self.subTest(defect=defect),patch.object(v,'inspect',return_value=current),patch.object(v,'run',side_effect=faulty):
                with self.assertRaises(ValueError):v.extract(self.timeline,self.video,[0,2],self.tool,self.tool,output)
                self.assertFalse(output.exists())

if __name__=='__main__':unittest.main()
