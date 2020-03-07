#!/usr/bin/env bash
# Execute this at the base of the streamlink repo.

set -e # stop on error

command -v makensis > /dev/null 2>&1 || { echo >&2 "makensis is required to build the installer. Aborting."; exit 1; }
command -v pynsist > /dev/null 2>&1 || { echo >&2 "pynsist is required to build the installer. Aborting."; exit 1; }
command -v convert > /dev/null 2>&1 || { echo >&2 "imagemagick is required to build the installer. Aborting."; exit 1; }
command -v inkscape > /dev/null 2>&1 || { echo >&2 "inkscape is required to build the installer. Aborting."; exit 1; }

# For travis nightly builds generate a version number with commit hash
STREAMLINK_VERSION=$(python setup.py --version)
STREAMLINK_VERSION_PLAIN="${STREAMLINK_VERSION%%+*}"
STREAMLINK_INSTALLER="streamlink-${STREAMLINK_VERSION/\+/_}"

# include the build number
STREAMLINK_VI_VERSION="${STREAMLINK_VERSION_PLAIN}.${TRAVIS_BUILD_NUMBER:-0}"

build_dir="$(pwd)/build"
build_dir_plugins="${build_dir}/lib/streamlink/plugins"
nsis_dir="${build_dir}/nsis"
files_dir="${build_dir}/files"
icons_dir="${files_dir}/icons"
# get the dist directory from an environment variable, but default to the build/nsis directory
dist_dir="${STREAMLINK_INSTALLER_DIST_DIR:-$nsis_dir}"
mkdir -p "${build_dir}" "${dist_dir}" "${nsis_dir}" "${files_dir}" "${icons_dir}"

echo "Building streamlink-${STREAMLINK_VERSION} package..." 1>&2
python setup.py build 1>&2

# https://github.com/streamlink/streamlink/issues/1223
echo "Create empty files."
old_files=(
  "afreecatv" "alieztv" "apac" "azubutv" "bambuser" "beam" "bliptv" "canlitv"
  "connectcast" "cyro" "daisuki" "disney_de" "dmcloud" "dmcloud_embed"
  "douyutv_blackbox" "filmon_us" "furstream" "gaminglive" "gomexp" "letontv"
  "livecodingtv" "livestation" "looch" "media_ccc_de" "meerkat" "neulion"
  "nineanime" "pcyourfreetv" "seemeplay" "servustv" "stream" "streamlive"
  "streamupcom" "tv8cat" "ufctv" "veetle" "viagame" "viasat_embed" "wattv"
  "aftonbladet" "aliez" "antenna" "arconai" "bongacams" "brittv" "cam4"
  "camsoda" "chaturbate" "expressen" "mips" "seetv" "speedrunslive" "streamboat"
  "vgtv" "weeb" "oldlivestream" "ok_live" "rte" "tvcatchup" "npo" "ovvatv"
)
for i in "${old_files[@]}"
do
    touch "${build_dir_plugins}/$i.py"
done

echo "Creating images" 1>&2
# Create images
for size in 16 32 48 256; do
  inkscape --without-gui --export-png="${icons_dir}/icon-${size}.png" -w ${size} -h ${size} icon.svg
done
convert "${icons_dir}"/icon-{16,32,48,256}.png "${icons_dir}/icon.ico"


echo "Building ${STREAMLINK_INSTALLER} installer..." 1>&2

cat > "${build_dir}/streamlink.cfg" <<EOF
[Application]
name=Streamlink
version=${STREAMLINK_VERSION}
entry_point=streamlink_cli.main:main
icon=${icons_dir}/icon.ico

[Python]
version=3.6.6
format=bundled

[Include]
; dep tree
;   streamlink+streamlink_cli
;       - pkg-resources (indirect)
;           - pyparsing
;           - packaging
;           - six
;       - iso639
;       - iso3166
;       - pycryptodome
;       - requests
;           - certifi
;           - idna
;           - urllib3
;           - socks / sockshandler
;       - websocket-client
;       - isodate
packages=pkg_resources
         six
         iso639
         iso3166
         requests
         urllib3
         idna
         chardet
         certifi
         websocket
         socks
         sockshandler
         isodate
pypi_wheels=pycryptodome==3.6.4

files=../win32/LICENSE.txt > \$INSTDIR
      ../build/lib/streamlink > \$INSTDIR\pkgs
      ../build/lib/streamlink_cli > \$INSTDIR\pkgs

[Command streamlink]
entry_point=streamlink_cli.main:main

[Command streamlinkw]
entry_point=streamlink_cli.main:main
console=false

[Build]
directory=nsis
nsi_template=installer_tmpl.nsi
installer_name=${dist_dir}/${STREAMLINK_INSTALLER}.exe
EOF

cat >"${build_dir}/installer_tmpl.nsi" <<EOF
!include "FileFunc.nsh"
!include "TextFunc.nsh"
[% extends "pyapp_msvcrt.nsi" %]

[% block modernui %]
    ; let the user review all changes being made to the system first
    !define MUI_FINISHPAGE_NOAUTOCLOSE
    !define MUI_UNFINISHPAGE_NOAUTOCLOSE

    ; add checkbox for opening the documentation in the user's default web browser
    !define MUI_FINISHPAGE_RUN
    !define MUI_FINISHPAGE_RUN_TEXT "Open online manual in web browser"
    !define MUI_FINISHPAGE_RUN_FUNCTION "OpenDocs"
    !define MUI_FINISHPAGE_RUN_NOTCHECKED

    ; make global installation mode the default choice
    ; see MULTIUSER_PAGE_INSTALLMODE macro below
    !undef MULTIUSER_INSTALLMODE_DEFAULT_CURRENTUSER

    Function OpenDocs
        ExecShell "" "https://streamlink.github.io/cli.html"
    FunctionEnd

    ; add checkbox for editing the configuration file
    !define MUI_FINISHPAGE_SHOWREADME
    !define MUI_FINISHPAGE_SHOWREADME_TEXT "Edit configuration file"
    !define MUI_FINISHPAGE_SHOWREADME_FUNCTION "EditConfig"
    !define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

    Function EditConfig
        SetShellVarContext current
        Exec '"\$WINDIR\notepad.exe" "\$APPDATA\streamlink\streamlinkrc"'
        SetShellVarContext all
    FunctionEnd

    ; constants need to be defined before importing MUI
    [[ super() ]]

    ; Add the product version information
    VIProductVersion "${STREAMLINK_VI_VERSION}"
    VIAddVersionKey /LANG=\${LANG_ENGLISH} "ProductName" "Streamlink"
    VIAddVersionKey /LANG=\${LANG_ENGLISH} "CompanyName" "Streamlink"
    VIAddVersionKey /LANG=\${LANG_ENGLISH} "FileDescription" "Streamlink Installer"
    VIAddVersionKey /LANG=\${LANG_ENGLISH} "LegalCopyright" ""
    VIAddVersionKey /LANG=\${LANG_ENGLISH} "FileVersion" "${STREAMLINK_VERSION}"
[% endblock %]

; UI pages
[% block ui_pages %]
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MULTIUSER_PAGE_INSTALLMODE
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
[% endblock ui_pages %]

[% block sections %]
[[ super()  ]]
SubSection /e "Bundled tools" bundled
    Section "rtmpdump" rtmpdump
        SetOutPath "\$INSTDIR\rtmpdump"
        File /r "${files_dir}\rtmpdump\*.*"
        SetShellVarContext current
        \${ConfigWrite} "\$APPDATA\streamlink\streamlinkrc" "rtmpdump=" "\$INSTDIR\rtmpdump\rtmpdump.exe" \$R0
        SetShellVarContext all
        SetOutPath -
    SectionEnd

    Section "FFMPEG" ffmpeg
        SetOutPath "\$INSTDIR\ffmpeg"
        File /r "${files_dir}\ffmpeg\*.*"
        SetShellVarContext current
        \${ConfigWrite} "\$APPDATA\streamlink\streamlinkrc" "ffmpeg-ffmpeg=" "\$INSTDIR\ffmpeg\ffmpeg.exe" \$R0
        SetShellVarContext all
        SetOutPath -
    SectionEnd
SubSectionEnd
[% endblock %]

[% block install_files %]
    [[ super() ]]
    ; Install config file
    SetShellVarContext current # install the config file for the current user
    SetOverwrite off # config file we don't want to overwrite
    SetOutPath \$APPDATA\streamlink
    File /r "${files_dir}\streamlinkrc"
    SetOverwrite ifnewer
    SetOutPath -
    SetShellVarContext all

    ; Add metadata
    ; hijack the install_files block for this
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\${PRODUCT_NAME}" "DisplayVersion" "${STREAMLINK_VERSION}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\${PRODUCT_NAME}" "Publisher" "Streamlink"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\${PRODUCT_NAME}" "URLInfoAbout" "https://streamlink.github.io/"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\${PRODUCT_NAME}" "HelpLink" "https://streamlink.github.io/"
    \${GetSize} "\$INSTDIR" "/S=0K" \$0 \$1 \$2
    IntFmt \$0 "0x%08X" \$0
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\\${PRODUCT_NAME}" "EstimatedSize" "\$0"
[% endblock %]

[% block uninstall_files %]
    [[ super() ]]
    RMDir /r "\$INSTDIR\rtmpdump"
    RMDir /r "\$INSTDIR\ffmpeg"
[% endblock %]

[% block install_commands %]
    ; Remove any existing bin dir from %PATH% to avoid duplicates
    [% if has_commands %]
    nsExec::ExecToLog '[[ python ]] -Es "\$INSTDIR\_system_path.py" remove "\$INSTDIR\bin"'
    [% endif %]
    [[ super() ]]
[% endblock install_commands %]

[% block install_shortcuts %]
    ; Remove shortcut from previous releases
    Delete "\$SMPROGRAMS\Streamlink.lnk"
[% endblock %]

[% block uninstall_shortcuts %]
    ; no shortcuts to be removed...
[% endblock %]

[% block mouseover_messages %]
[[ super() ]]

StrCmp \$0 \${sec_app} "" +2
  SendMessage \$R0 \${WM_SETTEXT} 0 "STR:\${PRODUCT_NAME} with embedded Python"

StrCmp \$0 \${bundled} "" +2
  SendMessage \$R0 \${WM_SETTEXT} 0 "STR:Extra tools used to play some streams"

StrCmp \$0 \${rtmpdump} "" +2
  SendMessage \$R0 \${WM_SETTEXT} 0 "STR:rtmpdump is used to play RTMP streams"

StrCmp \$0 \${ffmpeg} "" +2
  SendMessage \$R0 \${WM_SETTEXT} 0 "STR:FFMPEG is used to mux separate video and audio streams, for example high quality YouTube videos or DASH streams"

[% endblock %]
EOF

echo "Building Python 3 installer" 1>&2

# copy the streamlinkrc file to the build dir, we cannot use the Include.files property in the config file
# because those files will always overwrite, and for a config file we do not want to overwrite
cp "win32/streamlinkrc" "${files_dir}/streamlinkrc"

# copy the ffmpeg and rtmpdump directories to the install build dir
cp -r "win32/ffmpeg" "${files_dir}/"
cp -r "win32/rtmpdump" "${files_dir}/"

pynsist build/streamlink.cfg

echo "Success!" 1>&2
echo "The installer should be in ${dist_dir}." 1>&2
