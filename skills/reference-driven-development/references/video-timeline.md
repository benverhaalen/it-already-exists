# Recorded visible-transition evidence

Use `scripts/video_timeline.py` outside the implementer boundary when a recording
can reveal consequential intermediate behavior. This helper inspects one local
video stream and exports independently reviewed transition brackets to the
existing duration comparator. It is not a recording controller, frame classifier,
or device input latency instrument.

## Inspect actual PTS

Supply a reviewed FFprobe executable and a local MP4, MKV or MOV file:

```sh
python3 /path/to/skill/scripts/video_timeline.py inspect \
  --video /private/recording.mp4 --ffprobe /path/to/ffprobe \
  --output /private/timeline.json
```

The helper snapshots bounded input bytes, permits only local file protocols,
limits the probe to sixty seconds and four MiB of diagnostics, and requests
actual frame PTS from the first video stream. It records executable, input and
probe-output hashes, stream geometry and each decoded frame’s time. It rejects
missing PTS, duplicate/decreasing/nonfinite PTS, oversized geometry or more than
ten thousand frames. It never substitutes best-effort inferred timestamps. The
trusted media parser is not OS-sandboxed here; use an appropriate external
boundary for untrusted media. A hash identifies a decoder but does not qualify
its accuracy or dependencies.

FFprobe exposes per-frame metadata ([official documentation](https://ffmpeg.org/ffprobe.html)).
Scrcpy’s [recording documentation](https://github.com/Genymobile/scrcpy/blob/master/doc/recording.md)
explains that its recording timestamps are captured on the device. This motivates
preserving the original media time rather than host packet-arrival time. It does
not establish when an injected input reached the app or when a physical panel
presented a frame. No scrcpy binary was installed for this helper.

## Extract indexed evidence for review

Use the inspected timeline to produce a new directory of selected PNG frames:

```sh
python3 /path/to/skill/scripts/video_timeline.py frames \
  --timeline /private/timeline.json --video /private/recording.mp4 \
  --indices 8 9 --ffprobe /path/to/ffprobe --ffmpeg /path/to/ffmpeg \
  --output /private/frame-evidence
```

Indices must be distinct, increasing decoded-frame ordinals. The helper snapshots
the recording, freshly probes the same private bytes, and rejects stale video,
geometry or timelines before extraction. It uses FFmpeg's decoded ordinal
[`select` filter](https://ffmpeg.org/ffmpeg-filters.html#select_002c-aselect) with
[`passthrough` frame synchronization](https://ffmpeg.org/ffmpeg.html#Advanced-Video-options),
without seeking, resizing, resampling or automatic display rotation. The manifest
binds the recording, timeline, executables and each PNG hash to the corresponding
decoded index and PTS. PNG files do not themselves store these timestamps.

A batch allows at most 32 indices and 64 MiB of raw four-byte pixels. Use smaller
batches for large frames. The command retains the probe's sixty-second/four-MiB
diagnostic bounds. Publication rejects unexpected or missing output files,
oversized evidence and changed PNG header geometry; existing directories are
never overwritten. These checks trust the decoder and do not independently prove
pixel correctness, bound all parser allocations or provide an OS disk sandbox.
Keep any failed partial publication as unqualified evidence, not a finished packet.

## Review event meaning before export

Inspect decoded frames with their actual indices and timestamps. Select the
adjacent frames bracketing a meaningful visible transition:

```json
{
  "fixture": "declared reset conditions",
  "journey": "visible response",
  "events": [
    {"id":"start", "before_frame":0, "after_frame":1,
     "meaning":"The selected stimulus indicator first appears"},
    {"id":"done", "before_frame":8, "after_frame":9,
     "meaning":"The response first becomes visible"}
  ]
}
```

Those indices are illustrative. A reviewer must establish that each preceding
frame lacks the selected event and the following frame shows it. Neither the
helper nor adjacent frames prove capture completeness, no hidden intervening
event, or correct event classification. A sparse or lossy recording may not
support the desired tolerance. Do not invent an input event when only its later
visual consequence was captured.

Review contains `approved: true`, `reviewer`, `timeline_sha256`,
`video_sha256`, `artifact_sha256`, `contract_sha256` and `selection_sha256`.
Video and delivered-artifact digests hash the actual bytes; the other digests
use `comparison.canonical`. The reviewer separately checks the capture receipt
and correspondence between the installed build and recording. The hash binding
does not attest a device or make that correspondence true.

```sh
python3 /path/to/skill/scripts/video_timeline.py export \
  --timeline /private/timeline.json --video /private/recording.mp4 \
  --artifact /private/installed.apk --contract /private/contract.json \
  --selection /private/selected-events.json --review /private/review.json \
  --output /private/timing-packet.json
```

Output must be new. The comparator-ready packet carries midpoint `time`,
`time_bounds`, frame brackets, meaning, provenance and the fixed
`recorded_video_pts_seconds` basis. Keep the event definitions equivalent across
original and candidate. The [duration comparator](comparison.md#timing-uncertainty)
uses the bounds and cannot pass an ambiguous overlap solely because midpoints
match. Preserve the media and raw evidence outside the strict implementer; return
only independently reviewed behavioral discrepancies.

## Qualification limits

Variable presentation timestamps can contain long gaps between adjacent frames.
Do not substitute a nominal frame rate or index arithmetic for observed PTS.
Bind extracted frames to the freshly checked timeline and their hashes. Frame
extraction does not establish transition classification or input-to-response
latency. That requires an independently calibrated input marker and an explicit
clock relationship.

Seeded tests exercise variable PTS bounds, response discrepancies, changed input
and review rejection, and invalid brackets. A real original/candidate transition
comparison and device input clock calibration require separate qualification.
