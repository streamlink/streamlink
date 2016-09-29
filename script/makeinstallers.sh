#!/usr/bin/env bash
# Execute this at the base of the streamlink repo.

STREAMLINK_VERSION=$(python -c 'import streamlink; print(streamlink.__version__)')

mkdir -p build

cat > build/streamlink-py2.cfg <<EOF
[Application]
name=Streamlink
version=$STREAMLINK_VERSION
entry_point=streamlink_cli.main:main

[Python]
version=2.7.12

[Include]
packages=concurrent
         requests
         singledispatch
         streamlink
         streamlink_cli

files=../win32

[Command streamlink]
entry_point=streamlink_cli.main:main

[Build]
directory=nsis
installer_name=streamlink-$STREAMLINK_VERSION-py2.exe
EOF

echo "Building Python 2 installer"
pynsist build/streamlink-py2.cfg

cat > build/streamlink-py3.cfg <<EOF
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

files=../win32

[Command streamlink]
entry_point=streamlink_cli.main:main

[Build]
directory=nsis
installer_name=streamlink-$STREAMLINK_VERSION-py3.exe
EOF

echo "Building Python 3 installer"
pynsist build/streamlink-py3.cfg

echo "Success!"
echo "The installers should be in `pwd`/build/nsis."
