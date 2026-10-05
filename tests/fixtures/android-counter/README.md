# Owned Android observation fixture

This reference deliberately exposes a complete small journey: launch at zero,
increment through a native button after a 200 ms delay, terminate/reopen and
retain the count, then explicitly clear app data to reset. It supplies known
behavior for qualifying observation and comparison; success does not establish
reconstruction of arbitrary apps.

Build with separately installed free Android SDK platform/build tools 35 and a
compatible JDK. The helper installs nothing, uses a new private output directory
and creates an ephemeral development signing key:

```sh
python3 build.py --sdk /private/sdk --jdk /private/jdk/Contents/Home \
  --output /private/new-fixture-build
```

Keep generated APKs, keys, SDK files and captures outside this public repository.
Use only a task-owned device. Install `fixture.apk` and launch
`org.rdd.fixture/.Main`. Read count through the reviewed query
`adb -s SERIAL shell run-as org.rdd.fixture cat shared_prefs/fixture.xml`.
The XML count becomes the persistence/fixture oracle. A UI hierarchy or inspected
capture locates the actual button; do not assume a hard-coded coordinate works on
every screen. Reset requires stop, explicit permitted clear-data, launch, then a
new count-zero check. Launch alone preserves count.

For strict independent implementation, this source directory is analyst-side
reference material. The implementer gets reviewed observable behavior and
permitted evidence only. Do not mount this fixture source, build logs or the
complete repository into the strict worker. A fake backend or hand-written
candidate is a plumbing test, not evidence of real model reconstruction quality.
