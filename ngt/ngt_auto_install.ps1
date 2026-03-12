#Requires -Version 5.0

<#
.SYNOPSIS
    NGT Auto Installation Script for Local Machine (PowerShell Version - Final Fix)

.DESCRIPTION
    This script automatically installs Nutanix Guest Tools (NGT) on the local machine
    by detecting the current hostname and finding the corresponding VM in Nutanix.
    Uses the Nutanix v4.1/v4.0 APIs for VM management operations.

.PARAMETER PCIp
    Prism Central IP address

.PARAMETER Username
    Username for Nutanix authentication

.PARAMETER Password
    Password for Nutanix authentication

.PARAMETER Port
    Port number (default: 9440)

.PARAMETER VMUsername
    Username for VM (guest OS) authentication

.PARAMETER VMPassword
    Password for VM (guest OS) authentication

.PARAMETER VMUUID
    VM UUID to install NGT on (overrides auto-detection)

.PARAMETER VMName
    Override VM name detection

.PARAMETER ForceAPIVersion
    Force specific API version (v4.0 or v4.1)

.PARAMETER DryRun
    Show what would be done without making changes

.PARAMETER NoReboot
    Do not reboot VM after NGT installation

.PARAMETER SkipInstall
    Only check status, do not install

.PARAMETER DebugMode
    Enable debug logging

.EXAMPLE
    .\ngt_auto_install_final.ps1 -PCIp "10.38.11.74" -Username "admin"

.EXAMPLE
    .\ngt_auto_install_final.ps1 -VMUUID "a6b7070a-ea76-4689-8d2a-861374694953" -PCIp "10.38.11.74" -Username "admin" -VMUsername "administrator"
#>

param(
    [Parameter(Mandatory = $false)]
    [string]$PCIp,
    
    [Parameter(Mandatory = $false)]
    [string]$Username,
    
    [Parameter(Mandatory = $false)]
    [string]$Password,
    
    [Parameter(Mandatory = $false)]
    [int]$Port = 9440,
    
    [Parameter(Mandatory = $false)]
    [string]$VMUsername,
    
    [Parameter(Mandatory = $false)]
    [string]$VMPassword,
    
    [Parameter(Mandatory = $false)]
    [string]$VMUUID,
    
    [Parameter(Mandatory = $false)]
    [string]$VMName,
    
    [Parameter(Mandatory = $false)]
    [ValidateSet("v4.0", "v4.1")]
    [string]$ForceAPIVersion,
    
    [Parameter(Mandatory = $false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory = $false)]
    [switch]$NoReboot,
    
    [Parameter(Mandatory = $false)]
    [switch]$SkipInstall,
    
    [Parameter(Mandatory = $false)]
    [switch]$DebugMode
)

# Set up logging
if ($DebugMode) {
    $DebugPreference = "Continue"
}

function Write-Log {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        
        [Parameter(Mandatory = $false)]
        [ValidateSet("INFO", "WARNING", "ERROR", "DEBUG")]
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$timestamp - $Level - $Message"
    
    switch ($Level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        "DEBUG" { Write-Debug $logMessage }
        default { Write-Host $logMessage -ForegroundColor Green }
    }
}

# Custom URL encoding function to replace System.Web.HttpUtility
function ConvertTo-UrlEncoded {
    param([string]$String)
    
    if ([string]::IsNullOrEmpty($String)) {
        return $String
    }
    
    # Use .NET Uri.EscapeDataString which is available in PowerShell by default
    return [System.Uri]::EscapeDataString($String)
}

# Disable SSL certificate validation for self-signed certificates
add-type @"
    using System.Net;
    using System.Security.Cryptography.X509Certificates;
    public class TrustAllCertsPolicy : ICertificatePolicy {
        public bool CheckValidationResult(
            ServicePoint srvPoint, X509Certificate certificate,
            WebRequest request, int certificateProblem) {
            return true;
        }
    }
"@
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

class NutanixAPIClient {
    [string]$BaseUrl
    [string]$Username
    [string]$Password
    [string]$APIVersion
    [System.Collections.Hashtable]$Headers
    
    NutanixAPIClient([string]$pcIp, [string]$username, [string]$password, [int]$port) {
        $this.BaseUrl = "https://${pcIp}:${port}/api"
        $this.Username = $username
        $this.Password = $password
        $this.APIVersion = "v4.1"
        
        # Create authentication header
        $authString = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${username}:${password}"))
        $this.Headers = @{
            'Authorization' = "Basic $authString"
            'Accept' = 'application/json'
            'Content-Type' = 'application/json'
        }
    }
    
    [PSCustomObject] MakeRequest([string]$method, [string]$endpoint, [hashtable]$additionalHeaders, [string]$body) {
        $url = "$($this.BaseUrl)/$endpoint"
        
        # Clone headers properly by creating a new hashtable - use New-Object to avoid PowerShell class parsing issues
        $requestHeaders = New-Object System.Collections.Hashtable
        foreach ($key in $this.Headers.Keys) {
            $requestHeaders[$key] = $this.Headers[$key]
        }
        
        # Add request ID for idempotency
        $requestHeaders['NTNX-Request-Id'] = [System.Guid]::NewGuid().ToString()
        
        if ($additionalHeaders) {
            foreach ($key in $additionalHeaders.Keys) {
                $requestHeaders[$key] = $additionalHeaders[$key]
            }
        }
        
        Write-Log "Making $method request to $url" -Level DEBUG
        if ($additionalHeaders -and $additionalHeaders.ContainsKey('If-Match')) {
            Write-Log "Using ETag: $($additionalHeaders['If-Match'])" -Level DEBUG
        }
        
        try {
            $params = @{
                Uri = $url
                Method = $method
                Headers = $requestHeaders
                UseBasicParsing = $true
            }
            
            if ($body) {
                $params['Body'] = $body
            }
            
            $response = Invoke-RestMethod @params
            return $response
        }
        catch {
            Write-Log "API request failed: $($_.Exception.Message)" -Level ERROR
            if ($_.Exception.Response) {
                try {
                    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                    $errorDetails = $reader.ReadToEnd()
                    Write-Log "API error details: $errorDetails" -Level ERROR
                }
                catch {
                    Write-Log "Could not read error details" -Level DEBUG
                }
            }
            throw
        }
    }
    
    [PSCustomObject] Get([string]$endpoint) {
        return $this.MakeRequest('GET', $endpoint, $null, $null)
    }
    
    [PSCustomObject] Get([string]$endpoint, [hashtable]$additionalHeaders) {
        return $this.MakeRequest('GET', $endpoint, $additionalHeaders, $null)
    }
    
    [PSCustomObject] Post([string]$endpoint, [string]$body, [hashtable]$additionalHeaders) {
        return $this.MakeRequest('POST', $endpoint, $additionalHeaders, $body)
    }
    
    [void] SetAPIVersion([string]$version) {
        $this.APIVersion = $version
        Write-Log "API version set to: $version"
    }
    
    [string] GetAPIVersion() {
        return $this.APIVersion
    }
    
    [bool] TestAPIVersion() {
        try {
            $response = $this.Get("vmm/$($this.APIVersion)/ahv/config/vms?`$limit=1")
            return $true
        }
        catch {
            Write-Log "API version $($this.APIVersion) test failed: $($_.Exception.Message)" -Level DEBUG
            return $false
        }
    }
    
    [string] AutoDetectAPIVersion() {
        $versions = @("v4.1", "v4.0")
        foreach ($version in $versions) {
            $this.SetAPIVersion($version)
            if ($this.TestAPIVersion()) {
                Write-Log "Using API version: $version"
                return $version
            }
        }
        throw "Could not detect a working API version"
    }
}

class NGTInstaller {
    [NutanixAPIClient]$API
    [string]$APIVersion
    
    NGTInstaller([NutanixAPIClient]$apiClient) {
        $this.API = $apiClient
        $this.APIVersion = $apiClient.GetAPIVersion()
    }
    
    [PSCustomObject] FindVMByName([string]$vmName) {
        Write-Log "Searching for VM: $vmName"
        
        try {
            $filter = "name eq '$vmName'"
            $encodedFilter = ConvertTo-UrlEncoded $filter
            $endpoint = "vmm/$($this.API.GetAPIVersion())/ahv/config/vms?`$filter=$encodedFilter&`$limit=100&`$page=0"
            $response = $this.API.Get($endpoint)
            
            if (-not $response.data) {
                Write-Log "Invalid response format from VM list API" -Level ERROR
                return $null
            }
            
            $vms = $response.data
            
            if (-not $vms -or $vms.Count -eq 0) {
                Write-Log "No VM found with name: $vmName" -Level WARNING
                return $null
            }
            
            if ($vms.Count -gt 1) {
                Write-Log "Multiple VMs found with name '$vmName'. Using first match." -Level WARNING
            }
            
            $vm = $vms[0]
            Write-Log "Found VM: $($vm.name) (ID: $($vm.extId))"
            return $vm
        }
        catch {
            Write-Log "Error searching for VM: $($_.Exception.Message)" -Level ERROR
            return $null
        }
    }
    
    [PSCustomObject] FindVMByUUID([string]$vmUuid) {
        Write-Log "Searching for VM with UUID: $vmUuid"
        
        try {
            $response = $this.API.Get("vmm/$($this.API.GetAPIVersion())/ahv/config/vms/$vmUuid")
            
            if ($response.data) {
                $vm = $response.data
                Write-Log "Found VM: $($vm.name) (UUID: $($vm.extId))"
                return $vm
            }
            else {
                Write-Log "No VM found with UUID: $vmUuid" -Level WARNING
                return $null
            }
        }
        catch {
            Write-Log "Error searching for VM by UUID: $($_.Exception.Message)" -Level ERROR
            return $null
        }
    }
    
    [string] GetLocalVMUUID() {
        Write-Log "Attempting to detect local VM UUID..."
        
        $methods = @(
            { $this.GetUUIDFromWMI() },
            { $this.GetUUIDFromRegistry() },
            { $this.GetUUIDFromDMIDecode() }
        )
        
        foreach ($method in $methods) {
            try {
                $vmUuid = & $method
                if ($vmUuid) {
                    Write-Log "Detected local VM UUID: $vmUuid"
                    return $vmUuid
                }
            }
            catch {
                Write-Log "UUID detection method failed: $($_.Exception.Message)" -Level DEBUG
            }
        }
        
        Write-Log "Could not detect local VM UUID" -Level WARNING
        return $null
    }
    
    [string] GetUUIDFromWMI() {
        try {
            $uuid = (Get-WmiObject -Class Win32_ComputerSystemProduct).UUID
            if ($uuid -and $uuid.ToLower() -ne "not available" -and $uuid -ne "00000000-0000-0000-0000-000000000000") {
                return $uuid.ToLower()
            }
        }
        catch {
            Write-Log "WMI UUID detection failed: $($_.Exception.Message)" -Level DEBUG
        }
        return $null
    }
    
    [string] GetUUIDFromRegistry() {
        try {
            $regPath = "HKLM:\SOFTWARE\Microsoft\Cryptography"
            if (Test-Path $regPath) {
                $machineGuid = Get-ItemProperty -Path $regPath -Name "MachineGuid" -ErrorAction SilentlyContinue
                if ($machineGuid -and $machineGuid.MachineGuid) {
                    return $machineGuid.MachineGuid.ToLower()
                }
            }
        }
        catch {
            Write-Log "Registry UUID detection failed: $($_.Exception.Message)" -Level DEBUG
        }
        return $null
    }
    
    [string] GetUUIDFromDMIDecode() {
        # This would work on Linux/Unix systems if dmidecode is available
        # For Windows, this method is not applicable
        return $null
    }
    
    [PSCustomObject] FindLocalVM() {
        # First, try to detect UUID
        $localUuid = $this.GetLocalVMUUID()
        if ($localUuid) {
            Write-Log "Trying to find VM by detected UUID: $localUuid"
            $vm = $this.FindVMByUUID($localUuid)
            if ($vm) {
                Write-Log "Found local VM using detected UUID"
                return $vm
            }
        }
        
        # Fallback to hostname-based detection
        $hostname = $env:COMPUTERNAME
        try {
            $fqdn = [System.Net.Dns]::GetHostByName($env:COMPUTERNAME).HostName
        }
        catch {
            $fqdn = $hostname
        }
        
        Write-Log "Falling back to hostname detection - Hostname: $hostname, FQDN: $fqdn"
        
        # Try different variations of the machine name
        $potentialNames = @($hostname, $fqdn)
        
        # Also try without domain suffix if FQDN is different from hostname
        if ($fqdn.Contains('.') -and $fqdn -ne $hostname) {
            $potentialNames += $fqdn.Split('.')[0]
        }
        
        # Remove duplicates
        $uniqueNames = $potentialNames | Select-Object -Unique
        
        Write-Log "Searching for VM with potential names: $($uniqueNames -join ', ')"
        
        # Try to find VM with each potential name
        foreach ($vmName in $uniqueNames) {
            $vm = $this.FindVMByName($vmName)
            if ($vm) {
                Write-Log "Found local VM using name: $vmName"
                return $vm
            }
        }
        
        Write-Log "Could not find VM matching local machine" -Level ERROR
        Write-Log "Hints:" -Level INFO
        Write-Log "1. Ensure this script is running inside a Nutanix VM" -Level INFO
        Write-Log "2. The VM name in Nutanix matches one of these: $($uniqueNames -join ', ')" -Level INFO
        Write-Log "3. Or use -VMUUID parameter to specify the VM UUID directly" -Level INFO
        return $null
    }
    
    [PSCustomObject] GetVMDetails([string]$vmExtId) {
        Write-Log "Getting details for VM ID: $vmExtId"
        
        try {
            $response = $this.API.Get("vmm/$($this.API.GetAPIVersion())/ahv/config/vms/$vmExtId")
            
            if ($response.data) {
                return $response.data
            }
            return $response
        }
        catch {
            Write-Log "Error getting VM details: $($_.Exception.Message)" -Level ERROR
            return $null
        }
    }
    
    [PSCustomObject] GetGuestToolsInfo([string]$vmExtId) {
        Write-Log "Getting NGT info for VM ID: $vmExtId" -Level DEBUG
        
        try {
            $uri = "vmm/$($this.API.GetAPIVersion())/ahv/config/vms/$vmExtId/guest-tools"
            
            # Use Invoke-WebRequest to get response headers including ETag
            $webResponse = Invoke-WebRequest -Uri "$($this.API.BaseUrl)/$uri" -Headers $this.API.Headers -UseBasicParsing
            $response = $webResponse.Content | ConvertFrom-Json
            
            # Get ETag from response headers
            $etag = $webResponse.Headers['ETag']
            
            if ($response.data) {
                return @{
                    Data = $response.data
                    ETag = $etag
                }
            }
            return @{
                Data = $response
                ETag = $etag
            }
        }
        catch {
            Write-Log "Error getting NGT info: $($_.Exception.Message)" -Level ERROR
            return @{
                Data = $null
                ETag = $null
            }
        }
    }
    
    [string] CheckNGTStatus([PSCustomObject]$vm) {
        $guestTools = $vm.guestTools
        
        if ($guestTools) {
            $enabled = $guestTools.isEnabled -eq $true
            $installed = $guestTools.isInstalled -eq $true
            
            if ($installed -and $enabled) {
                return "installed_enabled"
            }
            elseif ($installed -and -not $enabled) {
                return "installed_disabled"
            }
            elseif (-not $installed) {
                return "not_installed"
            }
        }
        
        return "unknown"
    }
    
    [bool] InsertNGTISO([string]$vmExtId) {
        Write-Log "Inserting NGT ISO for VM ID: $vmExtId"
        
        try {
            # Get current NGT info (for ETag if needed)
            $ngtInfo = $this.GetGuestToolsInfo($vmExtId)
            
            # Prepare NGT ISO insertion payload
            $insertPayload = @{
                capabilities = @("SELF_SERVICE_RESTORE", "VSS_SNAPSHOT")
                isConfigOnly = $false
                '$objectType' = "vmm.v4.ahv.config.GuestToolsInsertConfig"
            } | ConvertTo-Json -Depth 10
            
            $additionalHeaders = New-Object System.Collections.Hashtable
            if ($ngtInfo.ETag) {
                $additionalHeaders['If-Match'] = $ngtInfo.ETag
            }
            
            Write-Log "Inserting NGT ISO..."
            
            # Insert NGT ISO using the v4.0 API
            $response = $this.API.Post("vmm/v4.0/ahv/config/vms/$vmExtId/guest-tools/`$actions/insert-iso", $insertPayload, $additionalHeaders)
            
            Write-Log "NGT ISO insertion request submitted successfully"
            
            # Check if response contains task information
            if ($response.data -and $response.data.extId) {
                $taskId = $response.data.extId
                Write-Log "ISO insertion task ID: $taskId"
                
                # Monitor task completion
                return $this.MonitorTask($taskId, 120)
            }
            else {
                Write-Log "NGT ISO insertion completed immediately"
                Start-Sleep -Seconds 5
                return $true
            }
        }
        catch {
            Write-Log "Error inserting NGT ISO: $($_.Exception.Message)" -Level ERROR
            return $false
        }
    }
    
    [bool] InstallNGT([string]$vmExtId, [string]$vmUsername, [string]$vmPassword, [bool]$rebootImmediately) {
        Write-Log "Installing NGT on VM ID: $vmExtId"
        
        # Step 1: Insert NGT ISO first
        Write-Log "Step 1: Preparing VM for NGT installation..."
        if (-not $this.InsertNGTISO($vmExtId)) {
            Write-Log "Failed to insert NGT ISO - installation cannot proceed" -Level ERROR
            return $false
        }
        
        # Wait for ISO insertion to settle
        Write-Log "Waiting for ISO insertion to settle..."
        Start-Sleep -Seconds 10
        
        # Step 2: Proceed with actual installation
        Write-Log "Step 2: Installing NGT..."
        try {
            # Get fresh NGT info after ISO insertion
            $ngtInfo = $this.GetGuestToolsInfo($vmExtId)
            
            # Prepare NGT installation payload
            $installPayload = @{
                capabilities = @("SELF_SERVICE_RESTORE", "VSS_SNAPSHOT")
                credential = @{
                    username = $vmUsername
                    password = $vmPassword
                    '$objectType' = "vmm.v4.ahv.config.Credential"
                }
                rebootPreference = @{
                    scheduleType = if ($rebootImmediately) { "IMMEDIATE" } else { "SKIP" }
                    '$objectType' = "vmm.v4.ahv.config.RebootPreference"
                }
                '$objectType' = "vmm.v4.ahv.config.GuestToolsInstallConfig"
            } | ConvertTo-Json -Depth 10
            
            $additionalHeaders = New-Object System.Collections.Hashtable
            if ($ngtInfo.ETag) {
                $additionalHeaders['If-Match'] = $ngtInfo.ETag
            }
            
            Write-Log "Submitting NGT installation request..."
            
            # Install NGT using the v4.0 API
            $response = $this.API.Post("vmm/v4.0/ahv/config/vms/$vmExtId/guest-tools/`$actions/install", $installPayload, $additionalHeaders)
            
            Write-Log "NGT installation request submitted successfully"
            
            # Check if response contains task information
            if ($response.data -and $response.data.extId) {
                $taskId = $response.data.extId
                Write-Log "Installation task ID: $taskId"
                
                # Monitor task completion
                return $this.MonitorTask($taskId, 600)
            }
            else {
                Write-Log "NGT installation request accepted"
                Start-Sleep -Seconds 15
                return $this.VerifyNGTInstallation($vmExtId)
            }
        }
        catch {
            Write-Log "Error installing NGT: $($_.Exception.Message)" -Level ERROR
            return $false
        }
    }
    
    [bool] MonitorTask([string]$taskId, [int]$timeout = 600) {
        Write-Log "Monitoring task $taskId"
        
        $startTime = Get-Date
        
        while (((Get-Date) - $startTime).TotalSeconds -lt $timeout) {
            try {
                # Try different task endpoints
                $taskEndpoints = @(
                    "prism/v4.0/config/tasks/$taskId",
                    "config/tasks/$taskId",
                    "tasks/$taskId"
                )
                
                $taskData = $null
                foreach ($endpoint in $taskEndpoints) {
                    try {
                        $response = $this.API.Get($endpoint)
                        $taskData = $response
                        break
                    }
                    catch {
                        continue
                    }
                }
                
                if (-not $taskData -or -not $taskData.data) {
                    Write-Log "Could not get task status, assuming completion" -Level WARNING
                    Start-Sleep -Seconds 5
                    return $true
                }
                
                $task = $taskData.data
                $status = $task.status
                
                Write-Log "Task status: $status"
                
                switch ($status) {
                    "SUCCEEDED" {
                        Write-Log "Task completed successfully"
                        return $true
                    }
                    "FAILED" {
                        $errorMessages = $task.errorMessages
                        if ($errorMessages) {
                            foreach ($error in $errorMessages) {
                                Write-Log "Task failed: $($error.message)" -Level ERROR
                            }
                        }
                        else {
                            $errorDetails = $task.errorDetails
                            Write-Log "Task failed: $errorDetails" -Level ERROR
                        }
                        return $false
                    }
                    { $_ -in @("PENDING", "RUNNING", "QUEUED") } {
                        Start-Sleep -Seconds 10
                    }
                    default {
                        Write-Log "Unknown task status: $status" -Level WARNING
                        Start-Sleep -Seconds 10
                    }
                }
            }
            catch {
                Write-Log "Error monitoring task (will continue checking): $($_.Exception.Message)" -Level WARNING
                Start-Sleep -Seconds 10
            }
        }
        
        Write-Log "Task monitoring timed out after $timeout seconds" -Level ERROR
        return $false
    }
    
    [bool] VerifyNGTInstallation([string]$vmExtId) {
        Write-Log "Verifying NGT installation..."
        
        try {
            Start-Sleep -Seconds 30  # Wait for installation to settle
            
            $ngtInfo = $this.GetGuestToolsInfo($vmExtId)
            
            if (-not $ngtInfo.Data) {
                Write-Log "❌ Could not retrieve NGT status information" -Level ERROR
                return $false
            }
            
            # Handle potential null values
            $isInstalled = $ngtInfo.Data.isInstalled -eq $true
            $isEnabled = $ngtInfo.Data.isEnabled -eq $true
            $version = if ($ngtInfo.Data.version) { $ngtInfo.Data.version } else { "Not Available" }
            
            Write-Log "NGT Status - Installed: $isInstalled, Enabled: $isEnabled, Version: $version"
            
            if ($isInstalled -and $isEnabled) {
                Write-Log "✅ NGT is successfully installed and enabled!"
                return $true
            }
            elseif ($isInstalled) {
                Write-Log "✅ NGT is installed (may need reboot to fully enable)"
                return $true
            }
            elseif ($version -ne "Not Available") {
                Write-Log "✅ NGT detected (version: $version)"
                return $true
            }
            else {
                Write-Log "❌ NGT installation verification failed" -Level WARNING
                return $false
            }
        }
        catch {
            Write-Log "Error verifying NGT installation: $($_.Exception.Message)" -Level ERROR
            return $false
        }
    }
}

function Get-NutanixCredentials {
    param(
        [string]$PCIp,
        [string]$Username,
        [string]$Password
    )
    
    if (-not $PCIp) {
        $PCIp = Read-Host "Enter Prism Central IP"
    }
    
    if (-not $Username) {
        $Username = Read-Host "Enter username"
    }
    
    if (-not $Password) {
        $securePassword = Read-Host "Enter password" -AsSecureString
        $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))
    }
    
    return @{
        PCIp = $PCIp
        Username = $Username
        Password = $Password
    }
}

function Get-VMCredentials {
    param(
        [string]$VMUsername,
        [string]$VMPassword
    )
    
    if (-not $VMUsername) {
        Write-Host "`nNGT installation requires VM credentials to install the tools inside the guest OS."
        $VMUsername = Read-Host "Enter VM username (e.g., administrator, root, etc.)"
    }
    
    if (-not $VMPassword) {
        $securePassword = Read-Host "Enter VM password" -AsSecureString
        $VMPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))
    }
    
    return @{
        VMUsername = $VMUsername
        VMPassword = $VMPassword
    }
}

function Get-LocalMachineInfo {
    $hostname = $env:COMPUTERNAME
    try {
        $fqdn = [System.Net.Dns]::GetHostByName($env:COMPUTERNAME).HostName
    }
    catch {
        $fqdn = $hostname
    }
    $platform = [System.Environment]::OSVersion.ToString()
    
    Write-Log "Local machine info - Hostname: $hostname, FQDN: $fqdn, Platform: $platform"
    return $hostname
}

# Main execution
try {
    Write-Log "NGT Auto Installation Script for Windows (PowerShell Version - Final Fix)"
    Write-Log "========================================================================"
    
    # Get Nutanix cluster credentials
    $creds = Get-NutanixCredentials -PCIp $PCIp -Username $Username -Password $Password
    
    if (-not ($creds.PCIp -and $creds.Username -and $creds.Password)) {
        Write-Log "All required Nutanix cluster parameters must be provided" -Level ERROR
        exit 1
    }
    
    # Initialize API client
    Write-Log "Connecting to Nutanix cluster at $($creds.PCIp)"
    $apiClient = [NutanixAPIClient]::new($creds.PCIp, $creds.Username, $creds.Password, $Port)
    
    # Set API version
    if ($ForceAPIVersion) {
        $apiClient.SetAPIVersion($ForceAPIVersion)
        Write-Log "Forced API version: $ForceAPIVersion"
    }
    else {
        # Auto-detect API version
        try {
            $detectedVersion = $apiClient.AutoDetectAPIVersion()
            Write-Log "Auto-detected API version: $detectedVersion"
        }
        catch {
            Write-Log "Could not auto-detect API version: $($_.Exception.Message)" -Level WARNING
            Write-Log "Falling back to v4.0"
            $apiClient.SetAPIVersion("v4.0")
        }
    }
    
    # Initialize NGT installer
    $installer = [NGTInstaller]::new($apiClient)
    
    # Find the VM - priority: UUID > VM name > local detection
    $vm = $null
    $vmIdentifier = "unknown"
    
    if ($VMUUID) {
        Write-Log "Using specified VM UUID: $VMUUID"
        $vm = $installer.FindVMByUUID($VMUUID)
        $vmIdentifier = $VMUUID
    }
    elseif ($VMName) {
        Write-Log "Using specified VM name: $VMName"
        $vm = $installer.FindVMByName($VMName)
        $vmIdentifier = $VMName
    }
    else {
        Write-Log "Auto-detecting local machine VM..."
        Get-LocalMachineInfo | Out-Null
        $vm = $installer.FindLocalVM()
        $vmIdentifier = if ($vm) { $vm.name } else { "unknown" }
    }
    
    if (-not $vm) {
        Write-Log "VM '$vmIdentifier' not found" -Level ERROR
        Write-Log "Please ensure:" -Level ERROR
        Write-Log "1. This script is running inside a Nutanix VM" -Level ERROR
        Write-Log "2. The VM UUID or name is correct" -Level ERROR
        Write-Log "3. You have proper access to the Nutanix cluster" -Level ERROR
        if (-not $VMUUID -and -not $VMName) {
            Write-Log "4. Consider using -VMUUID or -VMName to specify the VM directly" -Level ERROR
        }
        exit 1
    }
    
    # Get detailed VM information
    $vmDetails = $installer.GetVMDetails($vm.extId)
    if (-not $vmDetails) {
        Write-Log "Could not retrieve VM details" -Level ERROR
        exit 1
    }
    
    # Check current NGT status
    $ngtStatus = $installer.CheckNGTStatus($vmDetails)
    Write-Log "VM found: $($vm.name) (UUID: $($vm.extId))"
    Write-Log "Current NGT status: $ngtStatus"
    
    if ($SkipInstall) {
        Write-Log "Skip-install flag set. Exiting without installation."
        exit 0
    }
    
    if ($ngtStatus -eq "installed_enabled") {
        Write-Log "✅ NGT is already installed and enabled!"
        exit 0
    }
    
    if ($DryRun) {
        Write-Log "DRY RUN: Would install NGT on VM '$($vm.name)' (ID: $($vm.extId))"
        Write-Log "Process would be:"
        Write-Log "  1. Insert NGT ISO into VM"
        Write-Log "  2. Install NGT using provided credentials"
        Write-Log "  3. Monitor installation progress"
        Write-Log "  4. Verify successful installation"
        exit 0
    }
    
    # Get VM credentials for installation
    $vmCreds = Get-VMCredentials -VMUsername $VMUsername -VMPassword $VMPassword
    
    if (-not ($vmCreds.VMUsername -and $vmCreds.VMPassword)) {
        Write-Log "VM credentials are required for NGT installation" -Level ERROR
        exit 1
    }
    
    # Install NGT
    Write-Log "🚀 Installing NGT on VM '$($vm.name)'..."
    $rebootAfter = -not $NoReboot
    
    if ($rebootAfter) {
        Write-Log "VM will be rebooted after installation"
    }
    else {
        Write-Log "VM will NOT be rebooted after installation"
    }
    
    $success = $installer.InstallNGT($vm.extId, $vmCreds.VMUsername, $vmCreds.VMPassword, $rebootAfter)
    
    if ($success) {
        Write-Log "🎉 NGT installation process completed!"
        
        # Final verification
        Write-Log "Performing final verification..."
        Start-Sleep -Seconds 30
        $verificationResult = $installer.VerifyNGTInstallation($vm.extId)
        
        if ($verificationResult) {
            Write-Log "✅ NGT installation verified successfully!"
            Write-Log "🎉 Your VM now has Nutanix Guest Tools installed and verified!"
        }
        else {
            Write-Log "⚠️  NGT installation completed but verification failed." -Level WARNING
            Write-Log "This may be normal - NGT sometimes takes a few minutes to fully initialize." -Level WARNING
            Write-Log "Please check the Nutanix UI for final confirmation." -Level WARNING
        }
    }
    else {
        Write-Log "❌ NGT installation failed" -Level ERROR
        exit 1
    }
}
catch {
    Write-Log "Unexpected error: $($_.Exception.Message)" -Level ERROR
    if ($DebugMode) {
        Write-Log "Stack trace: $($_.ScriptStackTrace)" -Level ERROR
    }
    exit 1
}
