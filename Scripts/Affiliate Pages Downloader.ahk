; AutoHotkey script: Processes a fixed number of already-open browser tabs with deterministic UI actions.
; Uses ImageSearch first and falls back to predefined coordinates if detection fails.

#NoEnv
SendMode Input
CoordMode, Mouse, Screen
CoordMode, Pixel, Screen

TabCount := 3  ; Total number of tabs to process starting from the currently active tab.

; Fallback coordinates
ExtensionX := 1752
ExtensionY := 705
DownloadButtonX := 1590
DownloadButtonY := 64

; Resolve asset paths relative to this script
scriptDir := A_ScriptDir
extensionImg := scriptDir . "\..\.assets\Browser\Extension.png"
downloadImg := scriptDir . "\..\.assets\Browser\DownloadButton.png"
confirmationImg := scriptDir . "\..\.assets\Browser\ConfirmationFileDownloaded.png"

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

Gosub, ActivateChrome

Loop, %TabCount% {

    if (!running)
        break

    Gosub, RefreshCurrentTab
    if (!running)
        break

    Gosub, ClickExtensionIcon
    if (!running)
        break

    Gosub, ClickDownloadButton
    if (!running)
        break

    Gosub, WaitForDownloadConfirmation
    if (!running)
        break

    if (A_Index < TabCount) {
        Gosub, CloseCurrentTab
        if (!running)
            break
    }
}

completed := running  ; true if finished normally
running := false
isProcessing := false

if (completed) {
    MsgBox, 64, Automation Finished, The browser automation process completed successfully.
}

return


ActivateChrome:
WinActivate, ahk_exe chrome.exe
WinWaitActive, ahk_exe chrome.exe
WinMaximize, ahk_exe chrome.exe
Sleep, 1000
return


RefreshCurrentTab:
Send, ^r
waitMs := 5000
Gosub, WaitWithStop
return


ClickExtensionIcon:
found := false

ImageSearch, Px, Py, 0, 0, A_ScreenWidth, A_ScreenHeight, %extensionImg%
if (ErrorLevel = 0) {
    Click, %Px%, %Py%
    found := true
}

if (!found) {
    Click, %ExtensionX%, %ExtensionY%
}
return


ClickDownloadButton:

found := false
startTime := A_TickCount

while ((A_TickCount - startTime) < 3000) {

    if (!running)
        return

    ImageSearch, Px, Py, 0, 0, A_ScreenWidth, A_ScreenHeight, %downloadImg%

    if (ErrorLevel = 0) {
        Click, %Px%, %Py%
        found := true
        break
    }

    Sleep, 200
}

if (!found) {
    Click, %DownloadButtonX%, %DownloadButtonY%
}

return


WaitForDownloadConfirmation:

verificationCount := 0
maxVerifications := 36

Loop {

    if (!running)
        return

    ImageSearch, Px, Py, 0, 0, A_ScreenWidth, A_ScreenHeight, %confirmationImg%

    if (ErrorLevel = 0)
        break

    verificationCount++

    if (verificationCount >= maxVerifications)
        break

    waitMs := 5000
    Gosub, WaitWithStop
}

return


CloseCurrentTab:
Send, ^w
waitMs := 1000
Gosub, WaitWithStop
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