# Independently encoded synthetic wire vectors

`vectors.json` records output from the unmodified upstream Flutter Java
`StandardMessageCodec` at revision `d454b1b841d223f28bb725bb2928e2ac337b5611`.
`WireVectors.java` is the authored generator. It adds explicit custom tags
200/201, each wrapping one standard value; these are synthetic and imply no
application schema. The vectors contain no captured application data.

To reproduce, download `StandardMessageCodec.java` and `MessageCodec.java` from
that revision's `engine/src/flutter/shell/platform/android/io/flutter/plugin/common/`.
Their hashes are in the receipt. Keep Flutter's BSD license with downloaded
sources. Supply compile-only `androidx.annotation.NonNull` and `Nullable`
annotation stubs, `io.flutter.BuildConfig.DEBUG=true`, and `io.flutter.Log.e`
(the generator does not exercise the logging path). Compile those sources and
this generator with a JDK, then run `WireVectors` on a little-endian host. Its
lines contain the case name and encoded hex. No encoder/decoder production code
is substituted. The large string cases record hashes rather than 128 KiB of
repeated hex in the repository.

These are JVM wire controls, not Android-device execution or an iOS parity claim.
