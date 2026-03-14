; AutoHotkey script: Processes a user-defined number of already-open browser tabs with deterministic UI actions.
; Uses ImageSearch first and falls back to predefined coordinates if detection fails.

#NoEnv
SendMode Input
CoordMode, Mouse, Screen
CoordMode, Pixel, Screen

TabCount := 0  ; If 0, will read from Inputs/urls.txt or prompt user

; Coordinates
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
Urls := [] ; Holds URLs read from Inputs/urls.txt

F4::
running := !running

if (running) {

    if (TabCount = 0) {

        ; Read URLs from Inputs/urls.txt into the Urls object
        Urls := []
        if FileExist(urlsFile) {
            Loop, Read, %urlsFile%
            {
                line := Trim(A_LoopReadLine)
                if (line != "") {
                    ; Remove anything from the first whitespace to the end (strip filenames or extra text)
                    clean := RegExReplace(line, "\s+.*$")
                    clean := Trim(clean)
                    if (clean != "")
                        Urls.Push(clean)
                }
            }
        }

        ; If no URLs found, stop and inform the user
        TabCount := Urls.Length()
        if (TabCount = 0) {
            MsgBox, 48, Error, The file %urlsFile% is empty or contains no valid URLs.`nAutomation cannot start.
            running := false
            return
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

; Objects to collect tab indices per detection method
extMethods := {}
downloadMethods := {}
completionMethods := {}
closeMethods := {}

processedCount := 0
Gosub, ActivateChrome

; Record start time (milliseconds)
startTick := A_TickCount

Gosub, ActivateChrome

; Iterate through the loaded URLs and open each in a new tab before processing
for index, url in Urls {

    ; Open new tab and navigate to the URL via keyboard shortcuts
    if (!running)
        break

    ClipSaved := ClipboardAll
    Clipboard := url
    Sleep, 100

    Send, ^t
    Sleep, 200
    Send, ^l
    Sleep, 80
    Send, ^v
    Sleep, 100
    Send, {Enter}
    Sleep, 7000 ; wait for page to load

    Clipboard := ClipSaved

    ; Verify Chrome window is still running
    if !WinExist("ahk_id " targetChromeID) {
        MsgBox, 48, Automation Stopped, Chrome is not running. Process terminated at URL index %index%.
        break
    }

    currentTab := index

    ; (automation steps continue...)

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

    ; Record methods grouped by their detected method (collect tab indices)
    if (!extMethods.HasKey(extensionMethod))
        extMethods[extensionMethod] := []
    extMethods[extensionMethod].Push(currentTab)

    if (!downloadMethods.HasKey(downloadMethod))
        downloadMethods[downloadMethod] := []
    downloadMethods[downloadMethod].Push(currentTab)

    if (!completionMethods.HasKey(confirmationMethod))
        completionMethods[confirmationMethod] := []
    completionMethods[confirmationMethod].Push(currentTab)

    if (!closeMethods.HasKey(closeMethod))
        closeMethods[closeMethod] := []
    closeMethods[closeMethod].Push(currentTab)

    ; Close the current tab (product page) if there are more URLs to process
    if (index < TabCount) {
        Gosub, CloseCurrentTab
        if (!running)
            break
    }

    processedCount++
}

running := false
isProcessing := false

; Only show report when all URLs were processed
if (processedCount = TabCount) {
    elapsedSec := Round((A_TickCount - startTick) / 1000)
    formatted := format_execution_time(elapsedSec)
    ; Build condensed report grouped by method
    automationReport := ""

    for method, tabs in extMethods
        automationReport .= "Extension Click - " . method . ": " . joinArray(tabs) . "`n"

    automationReport .= "`n"
    for method, tabs in downloadMethods
        automationReport .= "Download Click - " . method . ": " . joinArray(tabs) . "`n"

    automationReport .= "`n"
    for method, tabs in completionMethods
        automationReport .= "Completion Detection - " . method . ": " . joinArray(tabs) . "`n"

    automationReport .= "`n"
    for method, tabs in closeMethods
        automationReport .= "Close Extension Tab - " . method . ": " . joinArray(tabs) . "`n"

    finalReport := "Execution Time: " . formatted . "`n`n" . automationReport
    MsgBox, 64, Automation Finished, %finalReport%
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
lastMethod := "Coordinates"
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
lastMethod := "Coordinates"
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
    lastMethod := "Coordinates"
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


joinArray(arr) {
    s := ""
    for index, val in arr
        s .= (s ? ", " : "") . val
    return s
}


format_execution_time(sec) {
    h := Floor(sec / 3600)
    m := Floor((sec - h*3600) / 60)
    s := sec - h*3600 - m*60

    if (m < 10)
        mStr := "0" . m
    else
        mStr := m

    if (s < 10)
        sStr := "0" . s
    else
        sStr := s

    if (h > 0)
        return h . ":" . mStr . ":" . sStr
    return mStr . ":" . sStr
}