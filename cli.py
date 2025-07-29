"""
Command-line interface for KVM backup system
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

from config import settings
from models import BackupMode, VMState
from vm_manager import LibvirtManager
from backup_manager import BackupManager
from logging_config import setup_logging, get_logger

app = typer.Typer(help="KVM Backup System - Modern backup solution for KVM/libvirt")
console = Console()


def init_logging():
    """Initialize logging system"""
    setup_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
        log_dir=settings.log_dir,
        log_file_max_size=settings.log_file_max_size,
    )


@app.command()
def list_vms(
    running_only: bool = typer.Option(False, "--running", "-r", help="Show only running VMs"),
    show_details: bool = typer.Option(False, "--details", "-d", help="Show detailed information")
):
    """List all virtual machines"""
    init_logging()
    logger = get_logger("kvm_backup.cli")
    
    try:
        with LibvirtManager() as vm_manager:
            if running_only:
                vms = vm_manager.list_running_vms()
                title = "Running Virtual Machines"
            else:
                vms = vm_manager.list_all_vms()
                title = "All Virtual Machines"
            
            if not vms:
                rprint("[yellow]No VMs found[/yellow]")
                return
            
            table = Table(title=title)
            table.add_column("Name", style="cyan")
            table.add_column("State", style="green")
            table.add_column("Memory (MB)", justify="right")
            table.add_column("vCPUs", justify="right")
            
            if show_details:
                table.add_column("UUID")
                table.add_column("Autostart")
                table.add_column("Disks", style="blue")
            
            for vm in vms:
                state_color = {
                    VMState.RUNNING: "green",
                    VMState.PAUSED: "yellow", 
                    VMState.SHUTDOWN: "red",
                    VMState.UNKNOWN: "dim"
                }.get(vm.state, "white")
                
                row = [
                    vm.name,
                    f"[{state_color}]{vm.state.value}[/{state_color}]",
                    str(vm.memory_mb),
                    str(vm.vcpus)
                ]
                
                if show_details:
                    row.extend([
                        vm.uuid,
                        "✓" if vm.autostart else "✗",
                        str(len(vm.disk_paths))
                    ])
                
                table.add_row(*row)
            
            console.print(table)
            logger.info("Listed VMs", vm_count=len(vms), running_only=running_only)
            
    except Exception as e:
        rprint(f"[red]Error listing VMs: {e}[/red]")
        logger.error("Failed to list VMs", error=str(e))
        raise typer.Exit(1)


@app.command()
def backup(
    vm_names: List[str] = typer.Argument(..., help="VM names to backup"),
    mode: BackupMode = typer.Option(BackupMode.INCREMENTAL, "--mode", "-m", help="Backup mode"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Simulate backup without actual transfer"),
    use_snapshots: bool = typer.Option(True, "--snapshots/--no-snapshots", help="Use snapshots (avoid VM downtime)"),
    compress: bool = typer.Option(True, "--compress/--no-compress", help="Enable compression"),
    job_name: Optional[str] = typer.Option(None, "--name", help="Backup job name")
):
    """Backup virtual machines"""
    init_logging()
    logger = get_logger("kvm_backup.cli")
    
    if job_name is None:
        job_name = f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    try:
        backup_manager = BackupManager(settings)
        
        # Validate VMs exist
        with LibvirtManager() as vm_manager:
            all_vms = [vm.name for vm in vm_manager.list_all_vms()]
            invalid_vms = set(vm_names) - set(all_vms)
            
            if invalid_vms:
                rprint(f"[red]Invalid VM names: {', '.join(invalid_vms)}[/red]")
                raise typer.Exit(1)
        
        # Create backup job
        job = backup_manager.create_backup_job(
            name=job_name,
            vm_names=vm_names,
            mode=mode,
            dry_run=dry_run,
            use_snapshots=use_snapshots,
            compress=compress
        )
        
        # Display job info
        panel_content = f"""
[bold]Job ID:[/bold] {job.id}
[bold]Name:[/bold] {job.name}
[bold]Mode:[/bold] {mode.value}
[bold]VMs:[/bold] {', '.join(vm_names)}
[bold]Snapshots:[/bold] {'✓' if use_snapshots else '✗'}
[bold]Compression:[/bold] {'✓' if compress else '✗'}
[bold]Dry Run:[/bold] {'✓' if dry_run else '✗'}
        """
        
        console.print(Panel(panel_content, title="Backup Job Configuration", border_style="blue"))
        
        if dry_run:
            rprint("[yellow]🧪 DRY RUN MODE - No actual transfer will be performed[/yellow]")
        
        # Execute backup with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running backup...", total=None)
            
            result = asyncio.run(backup_manager.execute_backup(job))
            
            progress.update(task, description="Backup completed")
        
        # Display results
        if result.status.value == "completed":
            rprint("[green]✓ Backup completed successfully![/green]")
            
            # Results table
            results_table = Table(title="Backup Results")
            results_table.add_column("VM Name")
            results_table.add_column("Status") 
            results_table.add_column("Method")
            results_table.add_column("Size (GB)", justify="right")
            
            for vm_name, vm_result in result.vm_results.items():
                status_color = "green" if vm_result.get('status') == 'success' else "red"
                size_gb = vm_result.get('size_bytes', 0) / (1024**3)
                
                results_table.add_row(
                    vm_name,
                    f"[{status_color}]{vm_result.get('status', 'unknown')}[/{status_color}]",
                    vm_result.get('method', 'unknown'),
                    f"{size_gb:.2f}"
                )
            
            console.print(results_table)
            
            # Summary
            duration = result.duration_seconds or 0
            total_gb = result.total_size_bytes / (1024**3)
            
            summary = f"""
[bold]Duration:[/bold] {duration:.1f} seconds
[bold]Total Size:[/bold] {total_gb:.2f} GB
[bold]Success Rate:[/bold] {result.success_rate:.1f}%
            """
            console.print(Panel(summary, title="Summary", border_style="green"))
            
        else:
            rprint(f"[red]✗ Backup failed: {result.error_message}[/red]")
            raise typer.Exit(1)
            
        logger.info("Backup completed via CLI", job_id=job.id, status=result.status.value)
        
    except Exception as e:
        rprint(f"[red]Backup error: {e}[/red]")
        logger.error("CLI backup failed", error=str(e))
        raise typer.Exit(1)


@app.command()
def snapshots(
    vm_name: str = typer.Argument(..., help="VM name"),
    action: str = typer.Argument(..., help="Action: list, create, delete"),
    snapshot_name: Optional[str] = typer.Option(None, "--name", help="Snapshot name for create/delete")
):
    """Manage VM snapshots"""
    init_logging()
    logger = get_logger("kvm_backup.cli")
    
    try:
        with LibvirtManager() as vm_manager:
            if action == "list":
                snapshots = vm_manager.list_snapshots(vm_name)
                
                if not snapshots:
                    rprint(f"[yellow]No snapshots found for VM '{vm_name}'[/yellow]")
                    return
                
                table = Table(title=f"Snapshots for {vm_name}")
                table.add_column("Name")
                table.add_column("Creation Time")
                table.add_column("Description")
                
                for snap in snapshots:
                    table.add_row(
                        snap.name,
                        snap.creation_time.strftime("%Y-%m-%d %H:%M:%S"),
                        snap.description
                    )
                
                console.print(table)
                
            elif action == "create":
                if not snapshot_name:
                    snapshot_name = f"manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                
                with console.status(f"Creating snapshot '{snapshot_name}'..."):
                    snapshot = vm_manager.create_snapshot(vm_name, snapshot_name)
                
                if snapshot:
                    rprint(f"[green]✓ Snapshot '{snapshot_name}' created successfully[/green]")
                else:
                    rprint(f"[red]✗ Failed to create snapshot '{snapshot_name}'[/red]")
                    raise typer.Exit(1)
                    
            elif action == "delete":
                if not snapshot_name:
                    rprint("[red]Snapshot name is required for delete action[/red]")
                    raise typer.Exit(1)
                
                with console.status(f"Deleting snapshot '{snapshot_name}'..."):
                    success = vm_manager.delete_snapshot(vm_name, snapshot_name)
                
                if success:
                    rprint(f"[green]✓ Snapshot '{snapshot_name}' deleted successfully[/green]")
                else:
                    rprint(f"[red]✗ Failed to delete snapshot '{snapshot_name}'[/red]")
                    raise typer.Exit(1)
                    
            else:
                rprint(f"[red]Invalid action '{action}'. Use: list, create, delete[/red]")
                raise typer.Exit(1)
                
        logger.info("Snapshot operation completed", vm_name=vm_name, action=action, snapshot_name=snapshot_name)
        
    except Exception as e:
        rprint(f"[red]Snapshot error: {e}[/red]")
        logger.error("CLI snapshot operation failed", vm_name=vm_name, action=action, error=str(e))
        raise typer.Exit(1)


@app.command()
def config():
    """Show current configuration"""
    init_logging()
    
    config_table = Table(title="KVM Backup Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    
    config_items = [
        ("Backup Server", settings.backup_server),
        ("Backup User", settings.backup_user),
        ("Remote Backup Dir", settings.remote_backup_dir),
        ("Local VM Dir", settings.local_vm_dir),
        ("Config Dir", settings.config_dir),
        ("Log Dir", settings.log_dir),
        ("Default Mode", settings.default_backup_mode),
        ("SSH Port", str(settings.ssh_port)),
        ("Snapshot Timeout", f"{settings.snapshot_timeout}s"),
        ("VM Shutdown Timeout", f"{settings.vm_shutdown_timeout}s"),
        ("API Host", settings.api_host),
        ("API Port", str(settings.api_port)),
    ]
    
    for setting, value in config_items:
        config_table.add_row(setting, value)
    
    console.print(config_table)


@app.command()
def server(
    host: str = typer.Option(None, "--host", help="Host to bind to"),
    port: int = typer.Option(None, "--port", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development")
):
    """Start the web API server"""
    init_logging()
    logger = get_logger("kvm_backup.api")
    
    host = host or settings.api_host
    port = port or settings.api_port
    
    try:
        import uvicorn
        from api import app as api_app
        
        rprint(f"[green]Starting KVM Backup API server on {host}:{port}[/green]")
        logger.info("Starting API server", host=host, port=port)
        
        uvicorn.run(
            "api:app",  # Simplified module path
            host=host,
            port=port,
            reload=reload,
            access_log=True
        )
        
    except ImportError as ie:
        rprint(f"[red]Import error: {ie}[/red]")
        rprint("[red]Make sure FastAPI and Uvicorn are installed: pip install fastapi uvicorn[/red]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Server error: {e}[/red]")
        logger.error("API server failed", error=str(e))
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
