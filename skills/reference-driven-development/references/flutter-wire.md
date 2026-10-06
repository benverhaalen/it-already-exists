# Inspect a Flutter message boundary

Use `scripts/flutter_wire_inspect.py` for a private binary StandardMessageCodec
capture. It runs offline and writes a new mode-0600 trace. It does not print
captured values. Keep traces private: strings and raw typed-array bytes can carry
credentials or personal data.

```sh
python3 scripts/flutter_wire_inspect.py capture.bin --byte-order little \
  --wrap-tag 200 --wrap-tag 201 --output trace.json
```

Specify the guest byte order. The output preserves type tags, absolute start/end
offsets, floating-point bits, padding bytes, typed arrays and ordered map pairs.
It retains duplicate or non-string map keys instead of coercing them to JSON
object keys. Integer values retain exact decimal JSON numerals; consumers must
use an integer-preserving JSON reader, not JavaScript `Number` for int64 values.
Non-finite floats use named strings alongside their original bits.

Unknown tags fail by default. `--wrap-tag` is only for an inspected custom codec
whose tag is followed by exactly one recursively encoded value. It does not infer
a Pigeon version, object field layout or enum semantics. Other custom formats
need a separate reader. Empty captures fail; an absent transport message is
different from an encoded null byte. Supply the exact message payload; method
calls and method envelopes need their own framing reader. Bytes from another
format can coincidentally decode and must not establish a channel's format.

The diagnostic limits input to 1 MiB, nesting to 64 levels and decoded work to
10,000 nodes/elements. It rejects truncation, unknown tags, invalid UTF-8 and
trailing bytes. Upstream readers skip padding without checking its contents;
this inspector records those bytes instead of imposing a new zero-pad rule.

## Qualify before drawing conclusions

The protocol is defined by Flutter's [Dart codec](https://github.com/flutter/flutter/blob/d454b1b841d223f28bb725bb2928e2ac337b5611/packages/flutter/lib/src/services/message_codecs.dart)
and [Android codec](https://github.com/flutter/flutter/blob/d454b1b841d223f28bb725bb2928e2ac337b5611/engine/src/flutter/shell/platform/android/io/flutter/plugin/common/StandardMessageCodec.java).
Scalar int32/int64 values have no padding. Scalar doubles and typed numeric
arrays align against the offset of the complete message, including enclosing
lists, custom tags and method-envelope prefixes. Do not concatenate standalone
encodings that contain alignment padding.

Regression inputs were produced by the pinned upstream Java encoder, executed
on a little-endian JVM. They cover primitives, nested wrappers, numeric arrays,
map keys, large integer text and both extended size widths. Additional authored
counterexamples cover a misplaced standalone double, malformed input, resource
bounds and duplicate map keys. This qualifies diagnostic decoding for those
cases; it does not establish full platform-channel or application equivalence.

Compare the trace with the versioned caller and native reader. Then test the
actual native codec and the complete original journey, including errors and
reopening. A diagnostic fixture failure must remain distinguishable from an app
failure. Preserve the first failed vector and its source revision when repairing
the observer.
