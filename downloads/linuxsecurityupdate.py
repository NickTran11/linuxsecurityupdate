#!/usr/bin/env python3
"""
kali_ssh_manager.py

Class-based SSH user management tool for Kali Linux.
- Add user with password
- Enable SSH service
- Configure sshd_config for password login
- Optional UFW rule
- Uses type casting and menu-driven interaction
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


class SSHSetup:
    def __init__(self):
        """Initialize constants"""
        self.username = "TonyXu234"
        self.password = "1234"
        self.service_name = "ssh"
        self.ssh_config = Path("/etc/ssh/sshd_config")

    # ------------------------ Utility Methods ------------------------

    def run(self, cmd: str, check=True, input_data=None):
        """Run a system command safely"""
        if isinstance(cmd, str):
            cmd = cmd.split()
        return subprocess.run(cmd, check=check, text=True, input=input_data, capture_output=False)

    def ensure_root(self):
        """Ensure the script runs as root"""
        if os.geteuid() != 0:
            print("[ERROR] Must be run as root or with sudo.")
            sys.exit(1)

    def backup_file(self, path: Path):
        """Backup config files before modification"""
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup = path.with_suffix(path.suffix + f".bak-{ts}")
        shutil.copy2(path, backup)
        print(f"[INFO] Backup created: {backup}")

    # ------------------------ Core Actions ------------------------

    def create_user(self):
        """Add new user and set password"""
        print(f"[ACTION] Creating user: {self.username}")
        # cast username and password to str just for demonstration of casting
        user = str(self.username)
        pw = str(self.password)
        # check if user exists
        if subprocess.run(["id", user], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            print(f"[INFO] User '{user}' already exists.")
        else:
            self.run(f"useradd -m -s /bin/bash {user}")
            print(f"[OK] User '{user}' created.")
        # set password
        self.run("chpasswd", input_data=f"{user}:{pw}\n")
        print(f"[OK] Password set for '{user}'.")

    def enable_ssh(self):
        """Install, enable and start OpenSSH"""
        print("[ACTION] Installing and enabling OpenSSH server...")
        self.run("apt update")
        self.run("apt install -y openssh-server")
        self.run(f"systemctl enable --now {self.service_name}")
        print(f"[OK] SSH service '{self.service_name}' started.")
        self.run(f"systemctl status {self.service_name}", check=False)

    def configure_sshd(self):
        """Enable password authentication in sshd_config"""
        print("[ACTION] Configuring sshd_config...")
        if not self.ssh_config.exists():
            print("[ERROR] /etc/ssh/sshd_config not found!")
            return

        self.backup_file(self.ssh_config)
        text = self.ssh_config.read_text().splitlines()
        output = []
        found_pw = found_root = False

        for line in text:
            stripped = line.strip()
            if stripped.startswith("PasswordAuthentication"):
                output.append("PasswordAuthentication yes")
                found_pw = True
            elif stripped.startswith("PermitRootLogin"):
                output.append("PermitRootLogin no")
                found_root = True
            else:
                output.append(line)

        if not found_pw:
            output.append("PasswordAuthentication yes")
        if not found_root:
            output.append("PermitRootLogin no")

        self.ssh_config.write_text("\n".join(output) + "\n")
        self.run("systemctl restart ssh")
        print("[OK] sshd_config updated and SSH restarted.")

    def allow_ufw(self):
        """Allow SSH through UFW firewall"""
        print("[ACTION] Configuring UFW...")
        if shutil.which("ufw") is None:
            print("[INFO] ufw not installed; skipping firewall config.")
            return
        self.run("ufw allow OpenSSH", check=False)
        self.run("ufw reload", check=False)
        print("[OK] SSH rule added in UFW.")

    # ------------------------ Menu System ------------------------

    def menu(self):
        """CLI menu for user to choose actions"""
        self.ensure_root()
        while True:
            print("\n========== System Update Manager ==========")
            print("1. Run all steps")
            print("2. Exit")
            try:
                choice = int(input("Enter your choice (1-2): ").strip())
            except ValueError:
                print("[ERROR] Invalid input. Please enter a number 1-2.")
                continue

             if choice == 1:
                self.create_user()
                self.enable_ssh()
                self.configure_sshd()
                self.allow_ufw()
                print(f"\n[COMPLETE] You can now SSH using:\nssh {self.username}@<KALI_IP> (password: {self.password})\n")
            elif choice == 2:
                print("Exiting...")
                break
            else:
                print("[ERROR] Invalid selection.")
            input("\nPress Enter to continue...")

# ------------------------ Main Entry ------------------------
if __name__ == "__main__":
    manager = SSHSetup()
    manager.menu()
