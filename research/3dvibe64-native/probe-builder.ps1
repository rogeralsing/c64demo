param([Parameter(Mandatory=$true)][string]$Builder)

$builderPath = (Resolve-Path -LiteralPath $Builder).Path
$parseTokens = $null
$parseErrors = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile(
    $builderPath, [ref]$parseTokens, [ref]$parseErrors)
[pscustomobject]@{
    powershellVersion = $PSVersionTable.PSVersion.ToString()
    edition = $PSVersionTable.PSEdition
    builder = $builderPath
    builderSha256 = (Get-FileHash -LiteralPath $builderPath -Algorithm SHA256).Hash.ToLowerInvariant()
    tokenCount = $parseTokens.Count
    parseErrors = @($parseErrors | ForEach-Object {
        [pscustomobject]@{message=$_.Message; line=$_.Extent.StartLineNumber}
    })
} | ConvertTo-Json -Depth 5
if ($parseErrors.Count -ne 0) { exit 1 }
