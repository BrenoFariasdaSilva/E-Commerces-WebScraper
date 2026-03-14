; AutoHotkey script: Processes a fixed number of already-open browser tabs with deterministic UI actions.
; Uses ImageSearch first and falls back to predefined coordinates if detection fails.

#NoEnv
SendMode Input
CoordMode, Mouse, Screen
CoordMode, Pixel, Screen

TabCount := 10  ; Total number of tabs to process starting from the currently active tab.

; Fallback coordinates
ExtensionX := 1752
ExtensionY := 705
DownloadButtonX := 1590
DownloadButtonY := 64

; Resolve asset paths relative to this script
scriptDir := A_ScriptDir
extensionImg := scriptDir . "\..\ .assets\Browser\Extension.png"
downloadImg := scriptDir . "\..\ .assets\Browser\DownloadButton.png"

; Normalize accidental space
extensionImg := StrReplace(extensionImg, "\.. ", "\..")
downloadImg := StrReplace(downloadImg, "\.. ", "\..")

running := false
isProcessing := false
waitMs := 0

F4::
    running := !running
    if (running) {
        SetTimer, StartAutomation, -10
    } else {
        SetTimer, StartAutomation, Off
    }
return

StartAutomation:
    if (!running)
        return

    if (isProcessing)
        return

    isProcessing := true

    ; Activate Chrome
    WinActivate, ahk_exe chrome.exe
    WinWaitActive, ahk_exe chrome.exe
    WinMaximize, ahk_exe chrome.exe
    Sleep, 1000

    Loop, %TabCount% {

        if (!running)
            break

        ; Refresh tab
        Send, ^r
        waitMs := 5000
        Gosub, WaitWithStop
        if (!running)
            break

        ; ---- Click extension icon (ImageSearch with fallback) ----
        found := false
        ImageSearch, Px, Py, 0, 0, A_ScreenWidth, A_ScreenHeight, %extensionImg%
        if (ErrorLevel = 0) {
            Click, %Px%, %Py%
            found := true
        }

        if (!found) {
            Click, %ExtensionX%, %ExtensionY%
        }

        waitMs := 2000
        Gosub, WaitWithStop
        if (!running)
            break

        ; ---- Click download button (ImageSearch with fallback) ----
        found := false
        ImageSearch, Px, Py, 0, 0, A_ScreenWidth, A_ScreenHeight, %downloadImg%
        if (ErrorLevel = 0) {
            Click, %Px%, %Py%
            found := true
        }

        if (!found) {
            Click, %DownloadButtonX%, %DownloadButtonY%
        }

        waitMs := 180000
        Gosub, WaitWithStop
        if (!running)
            break

        ; Switch tab
        if (A_Index < TabCount) {
            Send, ^{Tab}
            waitMs := 1000
            Gosub, WaitWithStop
            if (!running)
                break
        }
    }

    running := false
    isProcessing := false
return

WaitWithStop:
    elapsedMs := 0
    while (elapsedMs < waitMs) {
        if (!running)
            return
        Sleep, 100
        elapsedMs += 100
    }
return