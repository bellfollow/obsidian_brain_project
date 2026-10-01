# 레포(정본) -> ~/.claude, 볼트 루트(배포본)로 복사.
# 매핑은 Wiki.md의 "정본과 배포본" 표를 그대로 따른다.
# dry 확인: .\deploy.ps1 -WhatIf

[CmdletBinding(SupportsShouldProcess)]
param()

$RepoRoot  = Split-Path -Parent $PSScriptRoot
$ClaudeDir = "$HOME\.claude"
$VaultRoot = "G:\내 드라이브\obsidians\BellFollow"

$Pairs = @(
    @{ Src = "$RepoRoot\CLAUDE.md";              Dst = "$ClaudeDir\CLAUDE.md" }
    @{ Src = "$RepoRoot\rules\doc-folders.md";    Dst = "$ClaudeDir\rules\doc-folders.md" }
    @{ Src = "$RepoRoot\commands\ingest.md";      Dst = "$ClaudeDir\commands\ingest.md" }
    @{ Src = "$RepoRoot\commands\lint.md";        Dst = "$ClaudeDir\commands\lint.md" }
    @{ Src = "$RepoRoot\commands\log.md";         Dst = "$ClaudeDir\commands\log.md" }
    @{ Src = "$RepoRoot\commands\query.md";       Dst = "$ClaudeDir\commands\query.md" }
    @{ Src = "$RepoRoot\hooks\doc_writer.py";     Dst = "$ClaudeDir\hooks\doc_writer.py" }
    @{ Src = "$RepoRoot\hooks\raw_writer.py";     Dst = "$ClaudeDir\hooks\raw_writer.py" }
    @{ Src = "$RepoRoot\Wiki.md";                 Dst = "$VaultRoot\Wiki.md" }
    @{ Src = "$RepoRoot\_dashboard.md";           Dst = "$VaultRoot\_dashboard.md" }
)

foreach ($pair in $Pairs) {
    if (-not (Test-Path $pair.Src)) {
        Write-Warning "건너뜀 (레포에 없음): $($pair.Src)"
        continue
    }
    $dstDir = Split-Path -Parent $pair.Dst
    New-Item -ItemType Directory -Force -Path $dstDir -WhatIf:$WhatIfPreference | Out-Null
    Copy-Item $pair.Src $pair.Dst -Force -WhatIf:$WhatIfPreference
    Write-Output "복사: $($pair.Src) -> $($pair.Dst)"
}
