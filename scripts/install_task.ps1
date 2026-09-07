# Register keepalive.ps1 with Task Scheduler. Runs hourly.
# Replaces any existing task with the same name.

$Name = "ChordCollect"
$Ps   = "$PSScriptRoot\keepalive.ps1"

Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Ps`""

# Every hour, starting in one minute, no end date
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Hours 1)

# Do not stop on battery or idle conditions
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $Name `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Restart chord collection if it stops" | Out-Null

Get-ScheduledTask -TaskName $Name |
    Select-Object TaskName, State,
        @{n='NextRun';e={ (Get-ScheduledTaskInfo $_.TaskName).NextRunTime }}
