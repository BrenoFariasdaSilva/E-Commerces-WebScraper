; AutoHotkey script: Processes a user-defined number of already-open browser tabs with deterministic UI actions.
; Uses ImageSearch first and falls back to predefined coordinates if detection fails.

#NoEnv
SendMode Input
CoordMode, Mouse, Screen
CoordMode, Pixel, Screen

TabCount := 0  ; If 0, will read from Inputs/urls.txt or prompt user

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
mercadoLivreGoToImg := scriptDir . "\..\.assets\Browser\MercadoLivre-GoToProduct.png"
urlsFile := scriptDir . "\..\Inputs\urls.txt"

running := false
isProcessing := false
waitMs := 0
automationReport := ""
targetChromeID := ""

F4::
running := !running

if (running) {

    if (TabCount = 0) {

        ; Attempt to read number of URLs from Inputs/urls.txt
        ; Count URLs in the file (urlCount) and convert to tab switches (urls - 1)
        urlCount := 0
        if FileExist(urlsFile) {
            Loop, Read, %urlsFile%
            {
                line := Trim(A_LoopReadLine)
                if (line != "")
                    urlCount++
            }
        }

        if (urlCount > 0) {
            TabCount := urlCount
        } else {
            ; If file empty or missing, ask the user for number of URLs
            InputBox, userUrlCount, Automation Setup, Enter the number of URLs to process:, , 300, 140

            if (ErrorLevel) {
                running := false
                return
            }

            if (userUrlCount = "" || userUrlCount <= 0) {
                MsgBox, 48, Invalid Value, Please enter a valid number greater than 0.
                running := false
                return
            }

            if (userUrlCount > 0) {
                TabCount := userUrlCount
            } else
                TabCount := 0
        }
    }

        ; TabCount represents the number of URLs (no automatic -1 normalization)

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

    ; Verify Chrome window is still running
    if !WinExist("ahk_id " targetChromeID) {
        MsgBox, 48, Automation Stopped, Chrome is not running. Process terminated at tab %A_Index%.
        break
    }

    currentTab := A_Index

    ; Click "Go To Product" button for MercadoLivre, if present
    Gosub, ClickGoToProductButton

    ; Click extension icon
    Gosub, ClickExtensionIcon
    if (!running)
        break
    extensionMethod := lastMethod

    ; Click download button
    Gosub, ClickDownloadButton
    if (!running)
        break
    downloadMethod := lastMethod

    ; Wait for download confirmation
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


; --- Updated ActivateChrome to handle multiple windows ---
ActivateChrome:
SetTitleMatchMode, 2  ; Partial title match allowed
WinGet, chromeList, List, ahk_exe chrome.exe

if (chromeList = 0) {
    MsgBox, 48, Error, No Chrome windows found. Automation cannot start.
    running := false
    return
}

if (chromeList = 1) {
    ; Only one Chrome window — use it directly without prompting
    targetChromeID := chromeList1
} else {
    ; Multiple windows — ask the user to select which one to use
    windowsText := ""
    Loop, %chromeList%
    {
        thisID := chromeList%A_Index%
        WinGetTitle, thisTitle, ahk_id %thisID%
        windowsText .= A_Index ": " thisTitle "`n"
    }

    InputBox, selectedIndex, Select Chrome Window, Multiple Chrome windows detected.`nSelect the window index to use:`n`n%windowsText%, , 400, 300

    if (ErrorLevel || selectedIndex < 1 || selectedIndex > chromeList) {
        MsgBox, 48, Error, Invalid selection. Automation stopped.
        running := false
        return
    }

    targetChromeID := chromeList%selectedIndex%
}

WinActivate, ahk_id %targetChromeID%
WinWaitActive, ahk_id %targetChromeID%
WinMaximize, ahk_id %targetChromeID%
Sleep, 1000
return


RefreshCurrentTab:
Send, ^r
waitMs := 5000
Gosub, WaitWithStop
return

; --- Function to handle MercadoLivre webpage ---
ClickGoToProductButton:
found := false
ImageSearch, Px, Py, 0, 0, A_ScreenWidth, A_ScreenHeight, %mercadoLivreGoToImg%
if (ErrorLevel = 0) {
    Click, %Px%, %Py%
    lastMethod := "MercadoLivre Go To Product"
    found := true
    Sleep, 5000  ; <-- Wait 5s for page to load before proceeding
} else {
    lastMethod := "Not Found / Skipped"
}
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