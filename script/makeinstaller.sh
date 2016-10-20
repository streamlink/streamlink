#!/usr/bin/env bash
# Execute this at the base of the streamlink repo.

STREAMLINK_VERSION=$(python -c 'import streamlink; print(streamlink.__version__)')

mkdir -p build

cat > build/streamlink.cfg <<EOF
[Application]
name=Streamlink
version=$STREAMLINK_VERSION
entry_point=streamlink_cli.main:main

[Python]
version=3.5.2
format=bundled

[Include]
packages=requests
         streamlink
         streamlink_cli

files=../win32/rtmpdump > \$INSTDIR

[Command streamlink]
entry_point=streamlink_cli.main:main

[Build]
directory=nsis
installer_name=streamlink-$STREAMLINK_VERSION.exe
EOF

echo "Building Python 3 installer"
pynsist build/streamlink.cfg

echo "Success!"
echo "The installer should be in `pwd`/build/nsis."
