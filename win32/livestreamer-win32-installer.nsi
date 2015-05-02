# Livestreamer Windows installer script

# Set default compressor
SetCompressor lzma

###
### --- The PROGRAM_VERSION !define need to be updated with new Livestreamer versions ---
###

# Livestreamer program information
!define PROGRAM_NAME "Livestreamer"
!define PROGRAM_VERSION "1.12.2"
!define PROGRAM_WEB_SITE "http://livestreamer.io/"

# Python files generated with bbfreeze
!define LIVESTREAMER_PYTHON_BBFREEZE_OUTPUT_DIR "..\build-win32\livestreamer-${PROGRAM_VERSION}-win32"

# EnvVarUpdate
!include EnvVarUpdate.nsh
!include AdvReplaceInFile.nsh

# --- Interface settings ---

# Modern User Interface 2
!include MUI2.nsh

# Installer
!define MUI_COMPONENTSPAGE_SMALLDESC
!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_ABORTWARNING

# Uninstaller
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"
!define MUI_UNFINISHPAGE_NOAUTOCLOSE

# --- Start of Modern User Interface ---

# Welcome page
!define MUI_WELCOMEPAGE_TITLE_3LINES
!insertmacro MUI_PAGE_WELCOME

# License page
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"

# Components page
!insertmacro MUI_PAGE_COMPONENTS

# Let the user select the installation directory
!insertmacro MUI_PAGE_DIRECTORY

# Run installation
!insertmacro MUI_PAGE_INSTFILES

# Display 'finished' page
!define MUI_FINISHPAGE_NOREBOOTSUPPORT
!define MUI_FINISHPAGE_RUN "notepad.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Edit configuration file"
!define MUI_FINISHPAGE_RUN_PARAMETERS "$APPDATA\livestreamer\livestreamerrc"
!insertmacro MUI_PAGE_FINISH

# Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

# Language files
!insertmacro MUI_LANGUAGE "English"


# --- Functions ---

Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Do you want to completely remove $(^Name) and all of its components?" IDYES +2
  Abort
FunctionEnd


# --- Installation sections ---

# Compare versions
!include "WordFunc.nsh"

!define PROGRAM_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PROGRAM_NAME}"
!define PROGRAM_UNINST_ROOT_KEY "HKLM"

# Branding text
BrandingText "Livestreamer"

Name "${PROGRAM_NAME} ${PROGRAM_VERSION}"
OutFile "..\build-win32\livestreamer-${PROGRAM_VERSION}-win32-setup.exe"

InstallDir "$PROGRAMFILES\Livestreamer"

ShowInstDetails show
ShowUnInstDetails show

SectionGroup /e "Livestreamer"
# Install main application
Section "Livestreamer CLI" Section1
  SectionIn RO

  SetOutPath $INSTDIR
  File /r "${LIVESTREAMER_PYTHON_BBFREEZE_OUTPUT_DIR}\*.*"
  File "rtmpdump\librtmp.dll"

  SetOutPath "$APPDATA\livestreamer"

  SetOverwrite off
  File "livestreamerrc"

  Push @INSTDIR@
  Push $INSTDIR
  Push all
  Push all
  Push "$APPDATA\livestreamer\livestreamerrc"
  Call AdvReplaceInFile

  ${EnvVarUpdate} $0 "PATH" "A" "HKLM" "$INSTDIR"
SectionEnd

Section "RTMPDump" Section2
  SetOutPath "$INSTDIR\rtmpdump"
  File /r "rtmpdump\*.exe"
SectionEnd
SectionGroupEnd

Section -Uninstaller
  WriteUninstaller "$INSTDIR\uninstall-livestreamer.exe"
  WriteRegStr ${PROGRAM_UNINST_ROOT_KEY} "${PROGRAM_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PROGRAM_UNINST_ROOT_KEY} "${PROGRAM_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall-livestreamer.exe"
SectionEnd


LangString DESC_Section1 ${LANG_ENGLISH} "Install the Livestreamer CLI"
LangString DESC_Section2 ${LANG_ENGLISH} "Install RTMPDump, which is needed for RTMP streams"

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${Section1} $(DESC_Section1)
  !insertmacro MUI_DESCRIPTION_TEXT ${Section2} $(DESC_Section2)
!insertmacro MUI_FUNCTION_DESCRIPTION_END


# --- Uninstallation section(s) ---

Section Uninstall
  RmDir /r "$INSTDIR"

  SetShellVarContext all

  DeleteRegKey ${PROGRAM_UNINST_ROOT_KEY} "${PROGRAM_UNINST_KEY}"
  ${un.EnvVarUpdate} $0 "PATH" "R" "HKLM" "$INSTDIR"
SectionEnd
