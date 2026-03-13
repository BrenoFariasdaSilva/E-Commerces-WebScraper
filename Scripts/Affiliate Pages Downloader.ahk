; AutoHotkey script: Processes a fixed number of already-open browser tabs with deterministic UI actions.

#NoEnv
SendMode Input

TabCount := 10  ; Total number of tabs to process starting from the currently active tab.
ExtensionX := 0  ; X coordinate of the browser extension icon.
ExtensionY := 0  ; Y coordinate of the browser extension icon.
DownloadButtonX := 0  ; X coordinate of the Start download button in the extension panel.
DownloadButtonY := 0  ; Y coordinate of the Start download button in the extension panel.

running := false  ; Tracks whether automation is currently enabled.
isProcessing := false  ; Prevents concurrent automation runs.
waitMs := 0  ; Stores the current wait duration in milliseconds.

F4::
    running := !running  ; Toggle automation state on each F4 press.
    if (running) {  ; Start processing when toggled on.
        SetTimer, StartAutomation, -10  ; Queue a single immediate automation start.
    } else {  ; Stop processing when toggled off.
        SetTimer, StartAutomation, Off  ; Ensure no pending start timer remains active.
    }
return

StartAutomation:
    if (!running) {  ; Exit if automation was turned off before start.
        return  ; Stop this label execution safely.
    }

    if (isProcessing) {  ; Exit if a processing run is already active.
        return  ; Prevent concurrent action sequences.
    }

    isProcessing := true  ; Mark the automation run as active.

    Loop, %TabCount% {  ; Process exactly TabCount tabs in sequence.
        if (!running) {  ; Abort immediately when toggled off.
            break  ; Stop processing remaining tabs.
        }

        ; Refresh current browser tab
        Send, ^r  ; Send Ctrl+R to refresh the active tab.
        waitMs := 5000  ; Set post-refresh wait to 5 seconds.
        Gosub, WaitWithStop  ; Wait for page reload while allowing stop toggle.
        if (!running) {  ; Abort if stop was requested during wait.
            break  ; Stop processing remaining tabs.
        }

        ; Click extension icon
        MouseMove, %ExtensionX%, %ExtensionY%, 0  ; Move mouse to extension icon coordinates instantly.
        Click, left  ; Left-click the extension icon.
        waitMs := 2000  ; Set wait after opening extension panel to 2 seconds.
        Gosub, WaitWithStop  ; Wait for extension panel readiness.
        if (!running) {  ; Abort if stop was requested during wait.
            break  ; Stop processing remaining tabs.
        }

        ; Click Start download button
        MouseMove, %DownloadButtonX%, %DownloadButtonY%, 0  ; Move mouse to Start download button coordinates instantly.
        Click, left  ; Left-click the Start download button.
        waitMs := 180000  ; Set download processing wait to exactly 3 minutes.
        Gosub, WaitWithStop  ; Wait for downloads to finish while allowing stop toggle.
        if (!running) {  ; Abort if stop was requested during wait.
            break  ; Stop processing remaining tabs.
        }

        ; Switch to next browser tab
        if (A_Index < TabCount) {  ; Move to next tab only when more tabs remain to process.
            Send, ^{Tab}  ; Send Ctrl+Tab to switch to the next open tab.
            waitMs := 1000  ; Set post-tab-switch wait to 1 second.
            Gosub, WaitWithStop  ; Wait for tab switch completion.
            if (!running) {  ; Abort if stop was requested during wait.
                break  ; Stop processing remaining tabs.
            }
        }
    }

    running := false  ; Reset automation state after completion or stop.
    isProcessing := false  ; Mark processing run as finished.
return

WaitWithStop:
    elapsedMs := 0  ; Initialize elapsed wait counter.
    while (elapsedMs < waitMs) {  ; Iterate in bounded intervals until target delay is reached.
        if (!running) {  ; Exit wait immediately when stop is requested.
            return  ; Return control to caller label safely.
        }
        Sleep, 100  ; Sleep in short deterministic slices for responsive stopping.
        elapsedMs += 100  ; Advance elapsed wait counter by slice duration.
    }
return
