# Import the signing identity into the disposable, tag-only runner's user store.
$ErrorActionPreference = 'Stop'
$cert = Join-Path $env:RUNNER_TEMP 'signing.pfx'
try {
    [IO.File]::WriteAllBytes($cert, [Convert]::FromBase64String($env:WINDOWS_CERTIFICATE_BASE64))
    $password = ConvertTo-SecureString $env:WINDOWS_CERTIFICATE_PASSWORD -AsPlainText -Force
    $signer = Import-PfxCertificate -FilePath $cert -CertStoreLocation Cert:\CurrentUser\My -Password $password |
        Where-Object { $_.HasPrivateKey } | Select-Object -First 1
    if (!$signer -or !$env:WINDOWS_TIMESTAMP_URL) { throw 'Missing release signing identity or timestamp URL' }
    $sdk = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
    $tool = Get-ChildItem "$sdk\*\x64\signtool.exe" | Sort-Object FullName -Descending | Select-Object -First 1
    if (!$tool) { throw 'SignTool was not found in the Windows SDK' }
    $tool.DirectoryName >> $env:GITHUB_PATH
    "WINDOWS_SIGN_THUMBPRINT=$($signer.Thumbprint)" >> $env:GITHUB_ENV
    "WINDOWS_TIMESTAMP_URL=$env:WINDOWS_TIMESTAMP_URL" >> $env:GITHUB_ENV
} finally {
    Remove-Item $cert -ErrorAction SilentlyContinue
}
