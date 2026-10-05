# Source-free Android compiler environment

This is a qualified build route for the owned API35 Android reconstruction case,
not a universal Android project builder. It provides Node boundary probes,
Python, OpenJDK17 and official Android build-tools35.0.0/platform35. No target
application sources, original build scripts, emulator, model weights or inference
credentials belong in this image.

Download Google's Linux build-tools35 archive separately, after reviewing the
SDK terms. Obtain platform35 android.jar from the already authorized SDK install.
The pinned inputs are listed in prepare.py. The build-tools archive SHA256 was
measured after checking its size and SHA1 against Google's repository manifest.
Do not package or publish the SDK dependencies with this repository.

Run prepare.py with --archive, --platform-jar and a fresh --destination. It checks
both dependency hashes, bounded archive paths/types and emits an inventory and
Dockerfile. It does not download, accept licenses or copy arbitrary project files.
Build that destination with docker build --platform linux/amd64. The Node base is
pinned; Debian package resolution is live during provisioning, so rebuilds need
fresh qualification. Preserve the package inventory and final image ID. Build
network access ends at provisioning; generated implementation commands remain
in the offline boundary.

Before relying on an image, run qualify.py with --image (full local sha256 ID),
--spec (reviewed behavioral JSON), --project (fresh private probe directory) and
--receipt (fresh JSON output). It uses DockerCommands to qualify access, then
runs Node, Python, java/javac, aapt2, zipalign, D8 and apksigner checks through
that same boundary and preserves the Debian package inventory. Build and verify
an independently generated APK there. A successful Docker build alone
is insufficient. On ARM hosts this route uses x86 emulation; measure actual build
cost rather than assuming native performance.

Use frontier_worker.py with the image ID and a reviewed exact command catalog.
The implementer writes its own build script and signing key inside its project.
Install only a reviewed generated APK into a task-owned emulator. Bind the actual
APK bytes to candidate observations, compare them externally, and return reviewed
counterexamples. Signing keys are temporary development artifacts, never release
credentials. Build success, signature validity and toolchain probes do not prove
behavioral or visual fidelity.

The primary interfaces are documented by [Android AAPT2](https://developer.android.com/tools/aapt2)
and [D8](https://developer.android.com/tools/d8). The alternative
[Linux ARM SDK tools project](https://github.com/hamza72x/android-sdk-linux-arm64)
was inspected at commit 0e1d2404dad69ed30b435d70c6622c00b323ace6. Its README
advertised releases, but the release API returned 404 and no repository license
was located during this investigation; it was retained as a candidate and was
not executed or bundled.
