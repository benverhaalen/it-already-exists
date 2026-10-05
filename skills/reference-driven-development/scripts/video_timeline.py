#!/usr/bin/env python3
"""Bounded local video PTS inspection and reviewed transition brackets.

The decoder is trusted, not OS-sandboxed here. Media PTS is not input latency.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import tempfile
import uuid

from comparison import canonical, validate_contract
from offline_worker import ordinary, strict_json
from process import run


def read(path, limit=33554432):
    path = Path(path); ordinary(path)
    with path.open('rb') as stream:
        data = stream.read(limit+1)
    if len(data) > limit:
        raise ValueError('input exceeds byte limit')
    return data


def inspect(video, ffprobe):
    video = Path(video); tool = Path(ffprobe).resolve(strict=True)
    payload = read(video, 200*1024*1024)
    tool_hash = hashlib.sha256(read(tool, 200*1024*1024)).hexdigest()
    if video.suffix.lower() not in ('.mp4', '.mkv', '.mov'):
        raise ValueError('reviewed local MP4, MKV or MOV input required')
    with tempfile.TemporaryDirectory(prefix='rdd-video-') as name:
        root = Path(name); snapshot = root/('video'+video.suffix.lower())
        snapshot.write_bytes(payload)
        argv = [str(tool.resolve()), '-v', 'error', '-threads', '1',
                '-protocol_whitelist', 'file', '-select_streams', 'v:0',
                '-show_frames', '-show_streams', '-show_entries',
                'frame=pts_time,best_effort_timestamp_time:stream=width,height,time_base,codec_name',
                '-of', 'json', str(snapshot)]
        result = run(argv, root, timeout=60, max_bytes=4194304)
    if result['status'] != 'completed' or result['exit_code'] != 0:
        raise ValueError('video probe failed or exceeded bounds')
    metadata = strict_json(result['stdout'].decode())
    streams = metadata.get('streams', [])
    if len(streams) != 1 or any(type(streams[0].get(k)) is not int or not 0 < streams[0][k] <= 8192 for k in ('width', 'height')):
        raise ValueError('one bounded video stream required')
    frames = metadata.get('frames', [])
    if not 2 <= len(frames) <= 10000:
        raise ValueError('bounded multi-frame recording required')
    times = []
    for frame in frames:
        # Require actual PTS; best-effort timestamps alone may be interpolated.
        value = frame.get('pts_time')
        if not isinstance(value, str):
            raise ValueError('every decoded frame needs an actual presentation timestamp')
        value = float(value)
        if not math.isfinite(value) or times and value <= times[-1]:
            raise ValueError('strictly increasing finite presentation timestamps required')
        times.append(value)
    return dict(video_sha256=hashlib.sha256(payload).hexdigest(), video_bytes=len(payload),
                ffprobe_sha256=tool_hash, probe_output_sha256=hashlib.sha256(result['stdout']).hexdigest(),
                stream=streams[0], frames=[dict(index=i, pts_seconds=t) for i,t in enumerate(times)],
                limits=['Decoder executable is trusted; this helper is not a parser sandbox.',
                        'Video PTS does not prove device input time, capture completeness or artifact identity.',
                        'No frame-rate resampling or inferred timestamp replacement is performed.'])


def prepare(timeline, video, artifact, contract, selection, review):
    if any(not isinstance(v, dict) for v in (timeline, contract, selection, review)):
        raise ValueError('timeline, contract, selection and review must be objects')
    validate_contract(contract)
    bindings = dict(timeline_sha256=canonical(timeline), video_sha256=hashlib.sha256(read(video,200*1024*1024)).hexdigest(),
                    artifact_sha256=hashlib.sha256(read(artifact,200*1024*1024)).hexdigest(),
                    contract_sha256=canonical(contract), selection_sha256=canonical(selection))
    if review.get('approved') is not True or not isinstance(review.get('reviewer'), str) or not review['reviewer'].strip() or any(review.get(k) != v for k,v in bindings.items()):
        raise ValueError('explicit review must bind all current timeline/video/artifact/contract/selection inputs')
    if timeline.get('video_sha256') != bindings['video_sha256']:
        raise ValueError('timeline belongs to a different recording')
    frames = timeline.get('frames', []); times=[]
    for i,frame in enumerate(frames):
        t=frame.get('pts_seconds')
        if type(frame.get('index')) is not int or frame['index'] != i or type(t) not in (int,float) or not math.isfinite(t) or times and t<=times[-1]:
            raise ValueError('invalid ordered presentation timeline')
        times.append(t)
    if not 2<=len(times)<=10000:
        raise ValueError('bounded multi-frame timeline required')
    if set(selection) != {'fixture','journey','events'} or any(not isinstance(selection[k],str) or not selection[k].strip() for k in ('fixture','journey')):
        raise ValueError('explicit fixture, journey and reviewed events required')
    events=selection['events']
    if not isinstance(events,list) or not 2<=len(events)<=1000:
        raise ValueError('bounded multi-event selection required')
    run_id=uuid.uuid4().hex; observations=[]; seen=set(); last=-math.inf
    for event in events:
        if not isinstance(event,dict) or set(event)!={'id','before_frame','after_frame','meaning'}:
            raise ValueError('event needs identity, adjacent frame bracket and observable meaning')
        before,after=event['before_frame'],event['after_frame']
        if type(before) is not int or type(after) is not int or not 0<=before<after<len(times) or after!=before+1:
            raise ValueError('transition requires adjacent decoded frame indices')
        if not isinstance(event['id'],str) or not event['id'] or event['id'] in seen or not isinstance(event['meaning'],str) or not event['meaning'].strip():
            raise ValueError('distinct events and reviewed meanings required')
        bounds=[times[before],times[after]];mid=sum(bounds)/2
        if mid<last:raise ValueError('events must retain observed order')
        observations.append(dict(id=event['id'],run_id=run_id,time=mid,time_bounds=bounds,
                                 evidence=dict(before_frame=before,after_frame=after,meaning=event['meaning'])))
        seen.add(event['id']);last=mid
    return dict(run_id=run_id, artifact_sha256=bindings['artifact_sha256'],contract_sha256=bindings['contract_sha256'],
                fixture=selection['fixture'],journey=selection['journey'],timestamp_basis='recorded_video_pts_seconds',
                observations=observations,provenance=dict(**bindings,reviewer=review['reviewer']),
                limits=['Frame transition meanings and video-to-artifact correspondence are reviewed declarations.',
                        'Adjacent decoded frames do not prove no capture loss or no hidden intervening events.',
                        'These brackets describe visible transitions, not device input-to-display latency.'])


def extract(timeline, video, indices, ffprobe, ffmpeg, output):
    """Publish indexed PNG evidence only after re-probing the same private bytes.

    Selection is by decoded ordinal, never a seek or a synthesized frame rate.
    Tools are trusted. Bounds are operational limits, not an OS disk sandbox.
    """
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('frame output directory must be new')
    if not isinstance(timeline, dict) or not isinstance(indices, list) or not 1 <= len(indices) <= 32:
        raise ValueError('timeline object and one to 32 frame indices required')
    if any(type(i) is not int or i < 0 for i in indices) or indices != sorted(set(indices)):
        raise ValueError('frame indices must be distinct increasing nonnegative integers')
    video = Path(video)
    if video.suffix.lower() not in ('.mp4', '.mkv', '.mov'):
        raise ValueError('reviewed local MP4, MKV or MOV input required')
    payload = read(video, 200*1024*1024)
    tool = Path(ffmpeg).resolve(strict=True)
    tool_hash = hashlib.sha256(read(tool, 200*1024*1024)).hexdigest()
    with tempfile.TemporaryDirectory(prefix='rdd-frames-') as name:
        root = Path(name); snapshot = root/('video'+video.suffix.lower())
        snapshot.write_bytes(payload)
        current = inspect(snapshot, ffprobe)
        # Raw probe output includes paths/decoder metadata; compare decoded facts.
        for key in ('video_sha256', 'video_bytes', 'stream', 'frames'):
            if timeline.get(key) != current[key]:
                raise ValueError('timeline does not match freshly decoded recording')
        frames = current['frames']; width = current['stream']['width']; height = current['stream']['height']
        if indices[-1] >= len(frames):
            raise ValueError('selected frame index is outside recording')
        if len(indices)*width*height*4 > 64*1024*1024:
            raise ValueError('selected frames exceed 64 MiB raw pixel budget; use smaller batches')
        stage = root/'evidence'; stage.mkdir()
        expression = '+'.join('eq(n\\,%d)' % i for i in indices)
        argv = [str(tool), '-nostdin', '-v', 'error', '-threads', '1',
                '-protocol_whitelist', 'file', '-noautorotate', '-copyts', '-i', str(snapshot),
                '-map', '0:v:0', '-an', '-sn', '-dn', '-filter_threads', '1',
                '-vf', 'select='+expression, '-fps_mode', 'passthrough',
                '-c:v', 'png', '-threads', '1', '-start_number', '0',
                str(stage/'frame-%04d.png')]
        result = run(argv, root, timeout=60, max_bytes=4194304)
        if result['status'] != 'completed' or result['exit_code'] != 0:
            raise ValueError('frame extraction failed or exceeded bounds')
        expected = ['frame-%04d.png' % i for i in range(len(indices))]
        if sorted(p.name for p in stage.iterdir()) != expected:
            raise ValueError('frame extraction dropped or added output frames')
        evidence = []; total = 0
        for ordinal, index in enumerate(indices):
            data = read(stage/expected[ordinal], 16*1024*1024); total += len(data)
            if len(data) < 33 or data[:16] != b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' or struct.unpack('>II', data[16:24]) != (width, height):
                raise ValueError('extracted PNG geometry does not match recording')
            evidence.append(dict(index=index, pts_seconds=frames[index]['pts_seconds'],
                                 file=expected[ordinal], sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
        if total > 64*1024*1024:
            raise ValueError('encoded frame evidence exceeds byte budget')
        manifest = dict(schema='rdd-video-frames-v1', timeline_sha256=canonical(timeline),
                        video_sha256=current['video_sha256'], video_bytes=current['video_bytes'],
                        ffmpeg_sha256=tool_hash, ffprobe_sha256=current['ffprobe_sha256'],
                        fresh_probe_output_sha256=current['probe_output_sha256'],
                        stream=current['stream'], frames=evidence,
                        selection_basis='decoded_frame_index', autorotate=False,
                        limits=['Trusted decoder output; PNG header checks are not independent pixel qualification.',
                                'PTS is inherited from the freshly verified timeline, not stored in PNG files.',
                                'No resampling, seeking, resizing or automatic display rotation is performed.',
                                'Frame meanings, capture completeness and device input latency require separate evidence.'])
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')
        # copytree creates exclusively: a racing existing destination is not overwritten.
        shutil.copytree(stage, output)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='operation',required=True)
    p=sub.add_parser('inspect');p.add_argument('--video',required=True,type=Path);p.add_argument('--ffprobe',default=shutil.which('ffprobe'),type=Path);p.add_argument('--output',required=True,type=Path)
    p=sub.add_parser('export')
    for name in ('timeline','video','artifact','contract','selection','review','output'):p.add_argument('--'+name,required=True,type=Path)
    p=sub.add_parser('frames')
    for name in ('timeline','video','output'):p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--indices',required=True,nargs='+',type=int)
    for name in ('ffprobe','ffmpeg'):p.add_argument('--'+name,default=shutil.which(name),type=Path)
    args=parser.parse_args()
    try:
        if args.operation=='inspect':
            if args.ffprobe is None:raise ValueError('qualified ffprobe executable required')
            value=inspect(args.video,args.ffprobe)
        elif args.operation=='frames':
            if args.ffprobe is None or args.ffmpeg is None:raise ValueError('qualified ffprobe and ffmpeg executables required')
            extract(strict_json(read(args.timeline).decode()),args.video,args.indices,args.ffprobe,args.ffmpeg,args.output)
            return
        else:
            values={k:strict_json(read(getattr(args,k)).decode()) for k in ('timeline','contract','selection','review')}
            value=prepare(values['timeline'],args.video,args.artifact,values['contract'],values['selection'],values['review'])
        with args.output.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False)
    except (OSError,ValueError,KeyError,TypeError) as error:parser.exit(1,str(error)+'\n')


if __name__=='__main__':main()
