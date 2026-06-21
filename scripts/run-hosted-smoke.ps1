param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,
    [string]$Username = "",
    [string]$Password = "",
    [string]$InviteCode = "",
    [ValidateSet("W1", "W2", "W3", "W4")]
    [string]$Workflow = "W2",
    [string]$Input = "",
    [switch]$ExpectPilotReady,
    [switch]$RequireSignup,
    [switch]$SkipAuth,
    [switch]$SkipRun,
    [switch]$RealRun,
    [int]$Timeout = 120
)

$scriptPath = Join-Path $PSScriptRoot "hosted_smoke.py"
$args = @($scriptPath, "--base-url", $BaseUrl, "--workflow", $Workflow, "--timeout", "$Timeout")

if ($Username) {
    $args += @("--username", $Username)
}
if ($Password) {
    $args += @("--password", $Password)
}
if ($InviteCode) {
    $args += @("--invite-code", $InviteCode)
}
if ($Input) {
    $args += @("--input", $Input)
}
if ($ExpectPilotReady) {
    $args += "--expect-pilot-ready"
}
if ($RequireSignup) {
    $args += "--require-signup"
}
if ($SkipAuth) {
    $args += "--skip-auth"
}
if ($SkipRun) {
    $args += "--skip-run"
}
if ($RealRun) {
    $args += "--real-run"
}

python @args
