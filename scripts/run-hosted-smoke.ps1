param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl,
    [string]$Username = "",
    [string]$Password = "",
    [string]$InviteCode = "",
    [ValidateSet("AUTO", "W1", "W2", "W3", "W4", "W5", "W6")]
    [string]$Workflow = "W2",
    [string]$Input = "",
    [switch]$ExpectPilotReady,
    [string]$ExpectDetectedWorkflow = "",
    [string]$ExpectRouteStatus = "",
    [string]$ExpectRouteNoticeSubstring = "",
    [string]$ExpectW1Mode = "",
    [string]$ExpectRouteSummarySubstring = "",
    [switch]$ExpectW1SummaryBrief,
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
if ($ExpectDetectedWorkflow) {
    $args += @("--expect-detected-workflow", $ExpectDetectedWorkflow)
}
if ($ExpectRouteStatus) {
    $args += @("--expect-route-status", $ExpectRouteStatus)
}
if ($ExpectRouteNoticeSubstring) {
    $args += @("--expect-route-notice-substring", $ExpectRouteNoticeSubstring)
}
if ($ExpectW1Mode) {
    $args += @("--expect-w1-mode", $ExpectW1Mode)
}
if ($ExpectRouteSummarySubstring) {
    $args += @("--expect-route-summary-substring", $ExpectRouteSummarySubstring)
}
if ($ExpectW1SummaryBrief) {
    $args += "--expect-w1-summary-brief"
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
