; Define variables for later use in this script and from those variables passed
; in through the command-line.
!define PRODUCT_NAME "RIOS"
!define PRODUCT_VERSION "${VERSION} ${ARCHITECTURE}"
!define PRODUCT_BUILD_FOLDER "${DIST_FOLDER}"
!define UNINSTALL_PATH "Uninstall ${PRODUCT_NAME} ${PRODUCT_VERSION}"
!define PRODUCT_PUBLISHER "The Natural Capital Project"
!define PRODUCT_WEB_SITE "http://www.naturalcapitalproject.org"


; MUI has some graphical files that I want to define, which must be defined
; before the macros are declared.
!define MUI_WELCOMEFINISHPAGE_BITMAP "RIOS-stream-vertical.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "RIOS-stream-vertical.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "RIOS-header-stream.bmp"
!define MUI_HEADERIMAGE_UNBITMAP "RIOS-header-stream.bmp"
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\orange-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\orange-uninstall.ico"


; Set the compression size and type.
;SetCompressor /FINAL /SOLID lzma
;SetCompressorDictSize 64
SetCompressor /SOLID zlib


; MUI 1.67 compatible macro settings------
; Installer settings.
!include "MUI.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; MUI Uninstaller settings-------
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Language files
; First language declared is the default language.
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "Spanish"




Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\RIOS_${VERSION}_${ARCHITECTURE}_Setup.exe"
InstallDir "C:\Program Files\RIOS ${PRODUCT_VERSION}"
ShowInstDetails show

; This function (and these couple variables) allow us to dump the NSIS
; Installer log to a log file of our choice, which is very handy for debugging.
; To use, call it like this in the installation section.:
;
;   StrCpy $0 "$INSTDIR\install_log.txt"
;   Push $0
;   Call DumpLog
;
!define LVM_GETITEMCOUNT 0x1004
!define LVM_GETITEMTEXT 0x102D

Function DumpLog
    Exch $5
    Push $0
    Push $1
    Push $2
    Push $3
    Push $4
    Push $6

    FindWindow $0 "#32770" "" $HWNDPARENT
    GetDlgItem $0 $0 1016
    StrCmp $0 0 exit
    FileOpen $5 $5 "w"
    StrCmp $5 "" exit
        SendMessage $0 ${LVM_GETITEMCOUNT} 0 0 $6
        System::Alloc ${NSIS_MAX_STRLEN}
        Pop $3
        StrCpy $2 0
        System::Call "*(i, i, i, i, i, i, i, i, i) i \
            (0, 0, 0, 0, 0, r3, ${NSIS_MAX_STRLEN}) .r1"
        loop: StrCmp $2 $6 done
            System::Call "User32::SendMessageA(i, i, i, i) i \
            ($0, ${LVM_GETITEMTEXT}, $2, r1)"
            System::Call "*$3(&t${NSIS_MAX_STRLEN} .r4)"
            FileWrite $5 "$4$\r$\n"
            IntOp $2 $2 + 1
            Goto loop
        done:
            FileClose $5
            System::Free $1
            System::Free $3
    exit:
        Pop $6
        Pop $4
        Pop $3
        Pop $2
        Pop $1
        Pop $0
        Exch $5
FunctionEnd


; This function .onInit runs at the very beginning of the installer when it is
; launched.
Function .onInit
;Prompt the user for their UI language of choice
!insertmacro MUI_LANGDLL_DISPLAY

;This function creates a local key of some sort so that we can check to see if
;we already have an instance of this installer running on the computer.
 System::Call 'kernel32::CreateMutexA(i 0, i 0, t "RIOS ${PRODUCT_VERSION}") i .r1 ?e'
 Pop $R0

 StrCmp $R0 0 +3
   MessageBox MB_OK|MB_ICONEXCLAMATION "An instance of the RIOS ${PRODUCT_VERSION} installer is already running."
   Abort

 ; Show the snazzy RIOS splash screen once the installer has been verified it's
 ; the only instance running and the language has been selected.
 SetOutPath "$PLUGINSDIR"
 File "RIOS_splash_v.jpg"
 newadvsplash::show 2000 1000 5000 -1 "$PLUGINSDIR\RIOS_splash_v.jpg"
FunctionEnd

!define REG_KEY_FOLDER "${PRODUCT_PUBLISHER} ${PRODUCT_NAME} ${PRODUCT_VERSION}"
!define REGISTRY_PATH "Software\Microsoft\Windows\CurrentVersion\Uninstall\${REG_KEY_FOLDER}"
Section "Install" SEC01
  SetShellVarContext all
  SetOutPath "$INSTDIR"
  writeUninstaller "$INSTDIR\${UNINSTALL_PATH}.exe"

  ; Desired files are up one directory and in the timestamped RIOS folder.
  File /r "..\..\${PRODUCT_BUILD_FOLDER}\*"

  ; Create start  menu shortcuts.
  !define SMPATH "$SMPROGRAMS\${PRODUCT_NAME} ${PRODUCT_VERSION}"
  !define RIOS_ICON "$INSTDIR\RIOS-2-square.ico"

  CreateDirectory "${SMPATH}"
  CreateShortCut "${SMPATH}\${PRODUCT_NAME} (1) Investment Portfolio Adviser.lnk" "$INSTDIR\rios_ipa.exe" "" ${RIOS_ICON}
  CreateShortCut "${SMPATH}\${PRODUCT_NAME} (2) Portfolio Translator.lnk" "$INSTDIR\rios_porter.exe" "" ${RIOS_ICON}

  ; Write registry keys for convenient uninstallation via add/remove programs.
  ; Inspired by the example at
  ; nsis.sourceforge.net/A_simple_installer_with_start_menu_shortcut_and_installer
  WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayName"          "${PRODUCT_NAME} ${PRODUCT_VERSION}"
  WriteRegStr HKLM "${REGISTRY_PATH}" "UninstallString"      "$INSTDIR\${UNINSTALL_PATH}.exe"
  WriteRegStr HKLM "${REGISTRY_PATH}" "QuietUninstallString" "$INSTDIR\${UNINSTALL_PATH}.exe /S"
  WriteRegStr HKLM "${REGISTRY_PATH}" "InstallLocation"      "$INSTDIR"
  WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayIcon"          "$INSTDIR\rios_data\RIOS-2.ico"
  WriteRegStr HKLM "${REGISTRY_PATH}" "Publisher"            "${PRODUCT_PUBLISHER}"
  WriteRegStr HKLM "${REGISTRY_PATH}" "URLInfoAbout"         "${PRODUCT_WEB_SITE}"
  WriteRegStr HKLM "${REGISTRY_PATH}" "DisplayVersion"       "${PRODUCT_VERSION}"
  WriteRegDWORD HKLM "${REGISTRY_PATH}" "NoModify" 1
  WriteRegDWORD HKLM "${REGISTRY_PATH}" "NoRepair" 1

  ; Write the install log to a text file on disk.
  StrCpy $0 "$INSTDIR\install_log.txt"
  Push $0
  Call DumpLog
SectionEnd

Section "uninstall"
  ; Need to enforce execution level as admin.  See
  ; nsis.sourceforge.net/Shortcuts_removal_fails_on_Windows_Vista
  SetShellVarContext all
  rmdir /r "$SMPROGRAMS\${PRODUCT_NAME} ${PRODUCT_VERSION}"

  ; Delete the installation directory on disk
  rmdir /r "$INSTDIR"

  ; Delete the entire registry key for this version of RIOS.
  DeleteRegKey HKLM "${REGISTRY_PATH}"
SectionEnd
