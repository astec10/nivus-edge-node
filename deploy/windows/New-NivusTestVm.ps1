[CmdletBinding()]
param(
    [string]$IsoPath = (Join-Path $env:USERPROFILE 'Downloads\ubuntu-24.04.5-live-server-amd64.iso'),

    [string]$VmName = 'nivus-test-clean',

    [string]$BaseFolder = (Join-Path $env:USERPROFILE 'VirtualBox VMs'),

    [ValidateRange(1024, 65535)]
    [int]$SshHostPort = 2223
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$expectedIsoName = 'ubuntu-24.04.5-live-server-amd64.iso'
$isoUrl = 'https://releases.ubuntu.com/24.04/ubuntu-24.04.5-live-server-amd64.iso'
$expectedIsoSha256 = '97f3d7ffb032c3eb3b23d2c8be9cc76e60c2c1f2c0146ba5ba9fe01cafae0fd8'

if ($VmName -notmatch '^[A-Za-z0-9._-]+$') {
    throw 'Use um nome de VM com letras, números, ponto, hífen ou sublinhado.'
}

$vbox = Get-Command VBoxManage.exe -ErrorAction SilentlyContinue
if (-not $vbox) {
    $defaultVBox = Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'
    if (Test-Path -LiteralPath $defaultVBox -PathType Leaf) {
        $vboxPath = $defaultVBox
    } else {
        throw 'VBoxManage.exe não encontrado. Instale o Oracle VirtualBox ou ajuste o PATH.'
    }
} else {
    $vboxPath = $vbox.Source
}

function Invoke-VBox {
    param([string[]]$VBoxArgs)

    & $script:vboxPath @VBoxArgs
    if ($LASTEXITCODE -ne 0) {
        throw "VBoxManage falhou (código $LASTEXITCODE): $($VBoxArgs -join ' ')"
    }
}

$registeredVms = & $vboxPath list vms
if ($LASTEXITCODE -ne 0) {
    throw 'Não foi possível consultar as VMs registradas no VirtualBox.'
}
if (($registeredVms -join "`n") -match ('"' + [regex]::Escape($VmName) + '"\s+\{')) {
    throw "Já existe uma VM chamada $VmName. Nenhuma VM ou disco foi alterado."
}

$runningVms = & $vboxPath list runningvms
if ($LASTEXITCODE -ne 0) {
    throw 'Não foi possível verificar se já há VMs em execução.'
}
$runningVmLines = @($runningVms | Where-Object { $_ -match '^\s*"[^"]+"\s+\{' })
if ($runningVmLines.Count -gt 0) {
    throw 'Desligue as VMs em execução antes de criar a nova. Nenhuma VM ou disco foi alterado.'
}

$busyPort = Get-NetTCPConnection -State Listen -LocalPort $SshHostPort -ErrorAction SilentlyContinue
if ($busyPort) {
    throw "A porta local $SshHostPort já está em uso. Escolha outra com -SshHostPort."
}

$processors = Get-CimInstance Win32_Processor
$logicalThreads = [int](($processors | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum)
$hostRamGB = [double]((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$cpuCount = [Math]::Max(1, [Math]::Min(2, [Math]::Floor($logicalThreads / 2)))

if ($hostRamGB -lt 6) {
    throw 'O computador hospedeiro tem menos de 6 GB de RAM. Libere recursos ou use um host com mais memória antes de criar esta VM.'
} elseif ($hostRamGB -ge 12) {
    $memoryMB = 4096
} elseif ($hostRamGB -ge 8) {
    $memoryMB = 3072
} else {
    $memoryMB = 2048
    Write-Warning 'Com menos de 8 GB no host, a instalação do Ubuntu pode funcionar, mas o teste Docker do Nivus pode ficar limitado por memória.'
}
$availableHostRamMB = [int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024)
if ($availableHostRamMB -lt ($memoryMB + 2048)) {
    throw "Memória livre insuficiente no Windows: são necessários pelo menos $($memoryMB + 2048) MB livres para iniciar esta VM com margem para o host. Feche aplicativos e tente novamente."
}

$resolvedBase = [IO.Path]::GetFullPath($BaseFolder)
New-Item -ItemType Directory -Force -Path $resolvedBase | Out-Null
$vmFolder = Join-Path $resolvedBase $VmName
if (Test-Path -LiteralPath $vmFolder) {
    throw "A pasta já existe: $vmFolder. Escolha -VmName ou -BaseFolder diferente."
}

$root = [IO.Path]::GetPathRoot($resolvedBase)
$driveId = $root.TrimEnd('\')
$volume = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$driveId'"
if ($volume -and $volume.FreeSpace -lt 15GB) {
    throw 'O disco do host tem menos de 15 GB livres. Libere espaço antes de criar a VM.'
}

$iso = [IO.Path]::GetFullPath($IsoPath)
if ([IO.Path]::GetFileName($iso) -ne $expectedIsoName) {
    throw "Use a ISO oficial $expectedIsoName."
}
$isoFolder = Split-Path -Parent $iso
New-Item -ItemType Directory -Force -Path $isoFolder | Out-Null
$isoRoot = [IO.Path]::GetPathRoot($iso)
$isoDriveId = $isoRoot.TrimEnd('\')
$isoVolume = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$isoDriveId'"
if ($isoVolume -and $isoVolume.FreeSpace -lt 5GB) {
    throw 'O disco escolhido para a ISO precisa de pelo menos 5 GB livres.'
}

if (Test-Path -LiteralPath $iso -PathType Leaf) {
    $actualIsoSha256 = (Get-FileHash -LiteralPath $iso -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualIsoSha256 -ne $expectedIsoSha256) {
        throw 'A ISO já existe, mas o SHA-256 não confere. Ela foi preservada; corrija ou renomeie o arquivo antes de tentar novamente.'
    }
} else {
    $partialIso = "$iso.partial"
    if (Test-Path -LiteralPath $partialIso) {
        throw "Download parcial já existe em $partialIso. Confira e remova esse arquivo antes de tentar novamente."
    }
    Write-Host "Baixando a ISO oficial (~3,8 GB) para $iso; o download pode levar algum tempo."
    try {
        $bitsTransfer = Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue
        if ($bitsTransfer) {
            Start-BitsTransfer -Source $isoUrl -Destination $partialIso -ErrorAction Stop
        } else {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $webClient = New-Object Net.WebClient
            try { $webClient.DownloadFile($isoUrl, $partialIso) }
            finally { $webClient.Dispose() }
        }
        $downloadSha256 = (Get-FileHash -LiteralPath $partialIso -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($downloadSha256 -ne $expectedIsoSha256) {
            throw 'O SHA-256 do download não confere com o Ubuntu.'
        }
        Move-Item -LiteralPath $partialIso -Destination $iso
        $actualIsoSha256 = $downloadSha256
    } catch {
        if (Test-Path -LiteralPath $partialIso) {
            Remove-Item -LiteralPath $partialIso -Force -ErrorAction SilentlyContinue
        }
        throw "Falha ao baixar/verificar a ISO; nenhuma VM foi criada. $($_.Exception.Message)"
    }
}

Write-Host "VM nova: $VmName"
Write-Host "Ubuntu ISO: $expectedIsoName (SHA-256 $actualIsoSha256 conferido)"
Write-Host "Recursos calculados para o host: $cpuCount vCPU, $memoryMB MB RAM, VDI dinâmico de 32 GB"
Write-Host "SSH limitado ao host Windows: 127.0.0.1:$SshHostPort -> guest:22"
Write-Host 'A VM existente testev1 e o notebook Nivus não serão alterados.'

Invoke-VBox -VBoxArgs @('createvm', '--name', $VmName, '--ostype', 'Ubuntu_64', '--basefolder', $resolvedBase, '--register') | Out-Host
Invoke-VBox -VBoxArgs @('modifyvm', $VmName, '--memory', "$memoryMB", '--cpus', "$cpuCount", '--vram', '16', '--graphicscontroller', 'vmsvga', '--accelerate3d', 'off', '--nic1', 'nat', '--natpf1', "nivus-ssh,tcp,127.0.0.1,$SshHostPort,,22", '--boot1', 'dvd', '--boot2', 'disk') | Out-Host
Invoke-VBox -VBoxArgs @('storagectl', $VmName, '--name', 'SATA', '--add', 'sata', '--controller', 'IntelAhci', '--portcount', '2', '--bootable', 'on') | Out-Host

$diskPath = Join-Path $vmFolder "$VmName.vdi"
Invoke-VBox -VBoxArgs @('createmedium', 'disk', '--filename', $diskPath, '--size', '32768', '--format', 'VDI', '--variant', 'Standard') | Out-Host
Invoke-VBox -VBoxArgs @('storageattach', $VmName, '--storagectl', 'SATA', '--port', '0', '--device', '0', '--type', 'hdd', '--medium', $diskPath) | Out-Host
Invoke-VBox -VBoxArgs @('storageattach', $VmName, '--storagectl', 'SATA', '--port', '1', '--device', '0', '--type', 'dvddrive', '--medium', $iso) | Out-Host

Write-Host ''
Write-Host 'Iniciando o instalador do Ubuntu Server. Na instalação:'
Write-Host '  1. Use o disco virtual de 32 GB e instale Ubuntu Server minimal.'
Write-Host '  2. Marque OpenSSH server quando o instalador perguntar.'
Write-Host '  3. Crie uma conta e senha de teste; não as envie no chat.'
Write-Host "  4. Depois do reboot, conecte do Windows com: ssh -p $SshHostPort usuario@127.0.0.1"
Write-Host 'A regra NAT só escuta em 127.0.0.1; ela não publica SSH na LAN.'
Invoke-VBox -VBoxArgs @('startvm', $VmName, '--type', 'gui') | Out-Host
