#!/usr/bin/env python3
"""Build an owned fixture using separately installed SDK/JDK, without Gradle."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', required=True, type=Path)
    parser.add_argument('--jdk', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='new private directory')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    output, sdk, jdk = args.output.resolve(), args.sdk.resolve(), args.jdk.resolve()
    source = Path(__file__).resolve().parent
    tools = sdk/'build-tools/35.0.0'
    platform = sdk/'platforms/android-35/android.jar'
    classes = output/'classes'; classes.mkdir()
    dex = output/'dex'; dex.mkdir()
    def run(argv):
        import os
        completed = subprocess.run([str(x) for x in argv], cwd=output, env=dict(os.environ, JAVA_HOME=str(jdk)),
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        with (output/'build.log').open('ab') as stream:
            stream.write(completed.stdout)
        if completed.returncode:
            raise RuntimeError('fixture build command failed; inspect private build.log')
    run([jdk/'bin/javac', '--release', '8', '-classpath', platform, '-d', classes, source/'Main.java'])
    run([tools/'d8', '--lib', platform, '--output', dex, *sorted(classes.rglob('*.class'))])
    unsigned = output/'unsigned.apk'
    run([tools/'aapt2', 'link', '-I', platform, '--manifest', source/'AndroidManifest.xml',
         '--min-sdk-version', '26', '--target-sdk-version', '35', '-o', unsigned])
    with zipfile.ZipFile(unsigned, 'a', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(dex/'classes.dex', 'classes.dex')
    aligned = output/'aligned.apk'
    run([tools/'zipalign', '-f', '4', unsigned, aligned])
    key = output/'fixture-debug.p12'
    # Public conventional debug signing passwords; never a production key.
    run([jdk/'bin/keytool', '-genkeypair', '-keystore', key, '-storepass', 'android', '-keypass', 'android',
         '-alias', 'fixture', '-keyalg', 'RSA', '-keysize', '2048', '-validity', '2', '-dname', 'CN=RDD synthetic fixture'])
    apk = output/'fixture.apk'
    run([tools/'apksigner', 'sign', '--ks', key, '--ks-pass', 'pass:android', '--key-pass', 'pass:android', '--out', apk, aligned])
    run([tools/'apksigner', 'verify', apk])
    receipt = dict(apk_sha256=hashlib.sha256(apk.read_bytes()).hexdigest(), package='org.rdd.fixture',
                   source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (source/'Main.java', source/'AndroidManifest.xml')},
                   limits='Owned development fixture only. Build/sign verification does not establish runtime behavior.')
    (output/'build-receipt.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
