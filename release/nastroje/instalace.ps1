param(
    [ValidateSet('Instalovat', 'Odinstalovat')]
    [string]$Akce = 'Instalovat'
)

# Instalator ceske lokalizace pro Bellwright.
# 1) najde slozku hry (Steam knihovny), 2) nakopiruje Game.locres do Content/Localization/Game/cs,
# 3) prepne jazyk v GameUserSettings.ini na "cs" (se zalohou).

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$koren = Split-Path -Parent $PSScriptRoot           # slozka s .bat soubory
$zdroj = Join-Path $koren 'Bellwright\Content\Localization\Game\cs\Game.locres'
$iniSlozka = Join-Path $env:LOCALAPPDATA 'Bellwright\Saved\Config\Windows'
$ini = Join-Path $iniSlozka 'GameUserSettings.ini'

function Najdi-Hru {
    $kandidati = New-Object System.Collections.Generic.List[string]

    # 1) Steam knihovny z registru + libraryfolders.vdf
    foreach ($klic in 'HKCU:\Software\Valve\Steam', 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam') {
        try {
            $p = (Get-ItemProperty $klic -ErrorAction Stop)
            $steam = if ($p.SteamPath) { $p.SteamPath } else { $p.InstallPath }
            if ($steam) {
                $kandidati.Add((Join-Path $steam 'steamapps\common\Bellwright'))
                $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
                if (Test-Path $vdf) {
                    foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) {
                        $kandidati.Add((Join-Path ($m.Groups[1].Value -replace '\\\\', '\') 'steamapps\common\Bellwright'))
                    }
                }
            }
        } catch { }
    }
    # 2) bezne cesty na vsech discich
    foreach ($d in Get-PSDrive -PSProvider FileSystem) {
        $kandidati.Add("$($d.Root)SteamLibrary\steamapps\common\Bellwright")
        $kandidati.Add("$($d.Root)Steam\steamapps\common\Bellwright")
        $kandidati.Add("$($d.Root)Program Files (x86)\Steam\steamapps\common\Bellwright")
        $kandidati.Add("$($d.Root)Games\Bellwright")
    }

    $unikatni = $kandidati | Select-Object -Unique
    # nejdriv knihovna, kde Steam hru skutecne eviduje (appmanifest), pak jen podle souboru
    foreach ($k in $unikatni) {
        $manifest = Join-Path (Split-Path (Split-Path $k -Parent) -Parent) 'appmanifest_1812450.acf'
        if ((Test-Path $manifest) -and (Test-Path (Join-Path $k 'Bellwright\Content\Paks'))) { return $k }
    }
    foreach ($k in $unikatni) {
        $paks = Join-Path $k 'Bellwright\Content\Paks'
        if ((Test-Path $paks) -and ((Get-ChildItem $paks -Filter *.pak -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum -gt 100MB)) { return $k }
    }
    return $null
}

Write-Host ''
Write-Host '=== Bellwright – čeština (překlad zařídil TheraWoW.com) ===' -ForegroundColor Cyan
Write-Host ''

$hra = Najdi-Hru
if (-not $hra) {
    Write-Host 'Složku hry se nepodařilo najít automaticky.' -ForegroundColor Yellow
    Write-Host 'Zadej cestu ke složce Bellwright (ta, ve které je Bellwright.exe nebo podsložka Bellwright\Content):'
    $hra = (Read-Host 'Cesta').Trim('"', ' ')
    if (-not (Test-Path (Join-Path $hra 'Bellwright\Content\Paks'))) {
        Write-Host 'Na zadané cestě není nainstalovaný Bellwright. Konec.' -ForegroundColor Red
        exit 1
    }
}
Write-Host "Hra nalezena: $hra" -ForegroundColor Green

$cil = Join-Path $hra 'Bellwright\Content\Localization\Game\cs'

if ($Akce -eq 'Instalovat') {
    if (-not (Test-Path $zdroj)) {
        Write-Host "Chybí soubor $zdroj – rozbal prosím celý ZIP, ne jen .bat." -ForegroundColor Red
        exit 1
    }
    New-Item -ItemType Directory -Force -Path $cil | Out-Null
    Copy-Item $zdroj (Join-Path $cil 'Game.locres') -Force
    Write-Host "Zkopírováno: $cil\Game.locres" -ForegroundColor Green

    New-Item -ItemType Directory -Force -Path $iniSlozka | Out-Null
    if (Test-Path $ini) {
        $zaloha = "$ini.pred-cestinou.bak"
        if (-not (Test-Path $zaloha)) { Copy-Item $ini $zaloha }
        $obsah = Get-Content $ini -Raw
    } else {
        $obsah = ''
    }

    if ($obsah -match '(?m)^\s*Culture\s*=') {
        $obsah = [regex]::Replace($obsah, '(?m)^\s*Culture\s*=.*$', 'Culture=cs')
    } elseif ($obsah -match '(?m)^\[Internationalization\]') {
        $obsah = [regex]::Replace($obsah, '(?m)^\[Internationalization\]\s*$', "[Internationalization]`r`nCulture=cs")
    } else {
        if ($obsah -and -not $obsah.EndsWith("`n")) { $obsah += "`r`n" }
        $obsah += "`r`n[Internationalization]`r`nCulture=cs`r`n"
    }
    [System.IO.File]::WriteAllText($ini, $obsah, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "Jazyk přepnut na češtinu: $ini" -ForegroundColor Green
    Write-Host ''
    Write-Host 'HOTOVO. Spusť hru – texty budou česky.' -ForegroundColor Cyan
    Write-Host 'Po aktualizaci hry přes Steam stačí spustit Instalovat.bat znovu.'
}
else {
    if (Test-Path $cil) {
        Remove-Item $cil -Recurse -Force
        Write-Host "Odebráno: $cil" -ForegroundColor Green
    }
    if (Test-Path $ini) {
        $obsah = Get-Content $ini -Raw
        $obsah = [regex]::Replace($obsah, '(?m)^\s*Culture\s*=\s*cs\s*$', 'Culture=en')
        [System.IO.File]::WriteAllText($ini, $obsah, (New-Object System.Text.UTF8Encoding($false)))
        Write-Host 'Jazyk vrácen na angličtinu.' -ForegroundColor Green
    }
    Write-Host ''
    Write-Host 'HOTOVO. Čeština byla odebrána.' -ForegroundColor Cyan
}
