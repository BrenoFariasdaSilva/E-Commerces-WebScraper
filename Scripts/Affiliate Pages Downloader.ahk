; AutoHotkey script: Processes a user-defined number of already-open browser tabs with deterministic UI actions.
; Uses ImageSearch first and falls back to predefined coordinates if detection fails.

#NoEnv
SendMode Input
CoordMode, Mouse, Screen
CoordMode, Pixel, Screen

TabCount := 0  ; If 0, user will be prompted for the number of tabs

; Fallback coordinates
ExtensionX := 1752
ExtensionY := 705
DownloadButtonX := 1590
DownloadButtonY := 64
CloseDownloadTabX := 1905
CloseDownloadTabY := 148

; Resolve asset paths
scriptDir := A_ScriptDir
extensionImg := scriptDir . "\..\.assets\Browser\Extension.png"
downloadImg := scriptDir . "\..\.assets\Browser\DownloadButton.png"
confirmationImg := scriptDir . "\..\.assets\Browser\ConfirmationFileDownloaded.png"
closeDownloadTabImg := scriptDir . "\..\.assets\Browser\CloseDownloadTab.png"

running := false
isProcessing := false
waitMs := 0
automationReport := ""

F4::
running := !running

if (running) {

    if (TabCount = 0) {

        InputBox, userTabCount, Automation Setup, Enter the number of tabs to process:, , 300, 140

        if (ErrorLevel) {
            running := false
            return
        }

        if (userTabCount = "" || userTabCount <= 0) {
            MsgBox, 48, Invalid Value, Please enter a valid number greater than 0.
            running := false
            return
        }

        TabCount := userTabCount
    }

    SetTimer, StartAutomation, -10
}
else {
    SetTimer, StartAutomation, Off
}

return


StartAutomation:
if (!running)
    return

if (isProcessing)
    return

isProcessing := true
automationReport := ""

Gosub, ActivateChrome

Loop, %TabCount% {

    if (!running)
        break

    currentTab := A_Index

    Gosub, RefreshCurrentTab
    if (!running)
        break

    Gosub, ClickExtensionIcon
    if (!running)
        break
    extensionMethod := lastMethod

    Gosub, ClickDownloadButton
    if (!running)
        break
    downloadMethod := lastMethod

    Gosub, WaitForDownloadConfirmation
    if (!running)
        break
    confirmationMethod := lastMethod

    ; Close extension download tab
    Gosub, CloseExtensionDownloadTab
    if (!running)
        break
    closeMethod := lastMethod

    automationReport .= "Tab " currentTab ":`n"
    automationReport .= "  Extension Click: " extensionMethod "`n"
    automationReport .= "  Download Click: " downloadMethod "`n"
    automationReport .= "  Completion Detection: " confirmationMethod "`n"
    automationReport .= "  Close Extension Tab: " closeMethod "`n`n"

    if (A_Index < TabCount) {
        Gosub, CloseCurrentTab
        if (!running)
            break
    }
}

completed := running
running := false
isProcessing := false

if (completed) {
MsgBox, 64, Automation Finished, Automation process completed.`n`n%automationReport%
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
    lastMethod := "ImageSearch"
    return
}

Click, %ExtensionX%, %ExtensionY%
lastMethod := "Fallback Coordinates"
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
        lastMethod := "ImageSearch"
        return
    }

    Sleep, 200
}

Click, %DownloadButtonX%, %DownloadButtonY%
lastMethod := "Fallback Coordinates"
return


WaitForDownloadConfirmation:

verificationCount := 0
maxVerifications := 60  ; 60 attempts with 5s sleep = 300s (5 mins) max wait time

Loop {

    if (!running)
        return

    ImageSearch, Px, Py, 0, 0, A_ScreenWidth, A_ScreenHeight, %confirmationImg%

    if (ErrorLevel = 0) {
        lastMethod := "Image Detected"
        return
    }

    verificationCount++

    if (verificationCount >= maxVerifications) {
        lastMethod := "Timeout"
        return
    }

    waitMs := 5000
    Gosub, WaitWithStop
}

return


CloseExtensionDownloadTab:

found := false
ImageSearch, Px, Py, 0, 0, A_ScreenWidth, A_ScreenHeight, %closeDownloadTabImg%
if (ErrorLevel = 0) {
    Click, %Px%, %Py%
    lastMethod := "ImageSearch"
    found := true
}

if (!found) {
    Click, %CloseDownloadTabX%, %CloseDownloadTabY%
    lastMethod := "Fallback Coordinates"
}

Sleep, 500
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