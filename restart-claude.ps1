# Restart Claude Desktop. Nie rusza Claude Code CLI.
param([int]$DelaySeconds = 0)

$log = Join-Path $PSScriptRoot 'restart-claude.log'
function Log([string]$m) {
    ('{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m) | Add-Content -Path $log -Encoding UTF8
}

# Claude Desktop to aplikacja Electron (claude.exe z AnthropicClaude albo WindowsApps\Claude_*).
# Claude Code CLI tez nazywa sie claude.exe, wiec rozpoznajemy po sciezce albo plikach Electrona obok exe.
function Get-ClaudeDesktop {
    Get-Process -Name claude -ErrorAction SilentlyContinue | Where-Object {
        $p = $null
        try { $p = $_.Path } catch { }
        if (-not $p) { return $false }
        $dir = Split-Path $p
        ($p -match '\\AnthropicClaude\\') -or ($p -match '\\WindowsApps\\Claude_') -or
        (Test-Path (Join-Path $dir 'resources.pak')) -or (Test-Path (Join-Path $dir 'icudtl.dat'))
    }
}

function Start-ClaudeDesktop {
    if ($exe -match '\\WindowsApps\\') {
        $app = Get-StartApps | Where-Object { $_.Name -eq 'Claude' } | Select-Object -First 1
        if (-not $app) { $app = Get-StartApps | Where-Object { $_.Name -like 'Claude*' } | Select-Object -First 1 }
        if ($app) {
            Start-Process -FilePath 'explorer.exe' -ArgumentList ('shell:AppsFolder\' + $app.AppID)
            return ('AppsFolder ' + $app.AppID)
        }
        return $null
    }
    Start-Process -FilePath $exe
    return $exe
}

Log '--- start ---'
if ($DelaySeconds -gt 0) {
    Log ("czekam {0} s przed restartem" -f $DelaySeconds)
    Start-Sleep -Seconds $DelaySeconds
}

$before = @(Get-ClaudeDesktop)
if ($before.Count -eq 0) {
    Log 'BLAD: nie znaleziono dzialajacego Claude Desktop, nic nie zamykam'
    exit 1
}
$exe = $before[0].Path
Log ("Claude Desktop: {0} ({1} procesow)" -f $exe, $before.Count)

foreach ($proc in $before) {
    & taskkill.exe /F /T /PID $proc.Id 2>&1 | Out-Null
}

$t = 0
while ((@(Get-ClaudeDesktop).Count -gt 0) -and ($t -lt 20)) { Start-Sleep -Seconds 1; $t++ }
$left = @(Get-ClaudeDesktop)
if ($left.Count -gt 0) {
    Log ("zostalo {0} procesow, wymuszam Stop-Process" -f $left.Count)
    $left | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
}
Log ("zamkniety po {0} s" -f $t)
Start-Sleep -Seconds 5

$ok = $false
for ($attempt = 1; ($attempt -le 2) -and (-not $ok); $attempt++) {
    $how = Start-ClaudeDesktop
    Log ("uruchamiam (proba {0}): {1}" -f $attempt, $how)
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Seconds 1
        if (@(Get-ClaudeDesktop).Count -gt 0) { $ok = $true; break }
    }
}
if ($ok) { Log 'OK: Claude Desktop dziala ponownie' }
else { Log 'BLAD: Claude Desktop sie nie uruchomil, trzeba odpalic recznie' }
