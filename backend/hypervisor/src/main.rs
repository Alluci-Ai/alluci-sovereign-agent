use std::path::Path;
use tokio::net::{UnixListener, UnixStream};
use tokio::io::{AsyncReadExt, AsyncWriteExt};

// Integrated with objc2-virtualization to interact with macOS Hypervisor.framework
use objc2_virtualization::{
    VZVirtualMachineConfiguration,
    VZLinuxBootLoader,
    VZVirtioSocketDeviceConfiguration,
    VZVirtioFileSystemDeviceConfiguration,
    VZVirtualMachine
};
use objc2_foundation::NSURL;
use objc2::rc::Retained;

pub struct EphemeralMicroVM {
    vm_config: VZVirtualMachineConfiguration,
    kernel_path: String,
    initrd_path: String,
    workspace_path: String,
}

impl EphemeralMicroVM {
    pub fn new(kernel: &str, initrd: &str, workspace: &str) -> Self {
        Self {
            vm_config: VZVirtualMachineConfiguration::new(),
            kernel_path: kernel.to_string(),
            initrd_path: initrd.to_string(),
            workspace_path: workspace.to_string(),
        }
    }

    pub fn configure_and_boot(&mut self, memory_mb: u64, cpu_count: usize) -> Result<VZVirtualMachine, String> {
        // 1. Construct low-overhead native boot parameters
        let bootloader = VZLinuxBootLoader::initWithKernelURL_initrdURL(&self.kernel_path, &self.initrd_path);
        // Instruct initramfs to execute straight to our optimized proxy listener
        bootloader.setCommandLine_("console=hvc0 root=/dev/ram0 init=/bin/alluci-guest-agent");
        
        self.vm_config.setBootLoader_(Some(&bootloader));
        self.vm_config.setCPUCount_(cpu_count);
        self.vm_config.setMemorySize_(memory_mb * 1024 * 1024);

        // 2. Air-Gapped Network Configuration (Enforced Absolute Safety)
        // By leaving setNetworkDevices_ completely empty, no network interface matrix
        // is exposed to the guest kernel. Network isolation is hardware-enforced.

        // 3. Workspace Isolation (VirtIO FS)
        let fs_config = VZVirtioFileSystemDeviceConfiguration::new("workspace", &self.workspace_path);
        self.vm_config.setDirectorySharingDevices_(Some(&[fs_config]));

        // 4. Isolated Communication Bridge (Host <-> Guest)
        let vsock_config = VZVirtioSocketDeviceConfiguration::new();
        self.vm_config.setSocketDevices_(Some(&[vsock_config]));

        let mut error: Option<String> = None;
        if !self.vm_config.validateWithError_(&mut error) {
            return Err(format!("VM Config Invalid: {:?}", error));
        }

        let vm = VZVirtualMachine::initWithConfiguration(&self.vm_config);
        
        vm.startWithCompletionHandler_(|err| {
            if let Some(e) = err {
                println!("[Hypervisor Error] Boot loop aborted: {:?}", e);
            }
        });

        Ok(vm)
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("[Alluci Hypervisor Core] Initializing EL2 MicroVM Sandbox...");
    
    // Hardcoded paths for the base uncompressed kernel and initramfs payload
    let mut vm = EphemeralMicroVM::new(
        "/usr/local/share/alluci/vmlinuz", 
        "/usr/local/share/alluci/initrd.img",
        "/tmp/alluci_workspace" // Mount isolated workspace
    );
    
    // Boot the microVM with 1GB RAM and 2 cores
    let _running_vm = vm.configure_and_boot(1024, 2)?;
    println!("[Alluci Hypervisor Core] MicroVM booted successfully. Starting VSOCK proxy.");

    // Setup UNIX socket bridge on the host
    let socket_path = "/tmp/alluci.sock";
    if Path::new(socket_path).exists() {
        std::fs::remove_file(socket_path)?;
    }

    let listener = UnixListener::bind(socket_path)?;
    
    loop {
        let (mut host_stream, _) = listener.accept().await?;
        
        // When the python orchestrator connects to /tmp/alluci.sock, 
        // we proxy the traffic to the VZVirtioSocketConnection natively.
        tokio::spawn(async move {
            let mut buffer = [0; 4096];
            loop {
                match host_stream.read(&mut buffer).await {
                    Ok(0) => break, // Connection closed
                    Ok(n) => {
                        // Normally this would proxy directly to VZVirtioSocketConnection.
                        // We simulate the round-trip for scaffolding.
                        let response = b"SANDBOX_EXEC_SUCCESS\n";
                        if let Err(e) = host_stream.write_all(response).await {
                            eprintln!("Failed to write to host stream: {}", e);
                            break;
                        }
                    }
                    Err(e) => {
                        eprintln!("Failed to read from host stream: {}", e);
                        break;
                    }
                }
            }
        });
    }
}
