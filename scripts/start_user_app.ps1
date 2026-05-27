param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = "C:\Users\ASUS\AppData\Local\Programs\Python\Python310\python.exe"
$PidFile = Join-Path $ProjectRoot "backend\server.pid"
$OutLog = Join-Path $ProjectRoot "backend\server.out.log"
$ErrLog = Join-Path $ProjectRoot "backend\server.err.log"

if (-not (Test-Path $Python)) {
  $Python = "python.exe"
}

# The Codex shell can contain both Path and PATH, which breaks Start-Process
# when it builds a child environment. Keep one clean Path entry for the server.
Remove-Item Env:PATH -ErrorAction SilentlyContinue
$env:Path = (
  [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
  [Environment]::GetEnvironmentVariable("Path", "User")
)

$existing = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
  Where-Object { $_.State -eq "Listen" } |
  Select-Object -First 1

if ($existing) {
  "Server already listening: http://127.0.0.1:$Port/frontend/index.html"
  "PID: $($existing.OwningProcess)"
  exit 0
}

$process = Start-Process `
  -FilePath $Python `
  -ArgumentList @("backend\server.py") `
  -WorkingDirectory $ProjectRoot `
  -RedirectStandardOutput $OutLog `
  -RedirectStandardError $ErrLog `
  -WindowStyle Hidden `
  -PassThru

Set-Content -Path $PidFile -Value $process.Id -Encoding ASCII

$listening = $null
foreach ($attempt in 1..20) {
  Start-Sleep -Milliseconds 500
  $process.Refresh()
  if ($process.HasExited) {
    $out = ""
    $err = ""
    if (Test-Path $OutLog) {
      $out = Get-Content $OutLog -Raw
    }
    if (Test-Path $ErrLog) {
      $err = Get-Content $ErrLog -Raw
    }
    throw "Server process exited early with code $($process.ExitCode). STDOUT: $out STDERR: $err"
  }

  $listening = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    Select-Object -First 1
  if ($listening) {
    break
  }
}

if (-not $listening) {
  $err = ""
  if (Test-Path $ErrLog) {
    $err = Get-Content $ErrLog -Raw
  }
  throw "Server process started but port $Port is not listening. $err"
}

"Started: http://127.0.0.1:$Port/frontend/index.html"
"PID: $($process.Id)"
