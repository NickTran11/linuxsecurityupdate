#!/usr/bin/env python3
"""
linuxsecurityupdate.py

Creates user Customer with password 1234, optionally adds to sudo,
installs & enables OpenSSH server, enables PasswordAuthentication in sshd_config,
and can add a UFW rule for OpenSSH.

RUN AS ROOT:
  sudo python3 linuxsecurityupdate.py [--sudo] [--allow-ufw] [--install-fail2ban]

SECURITY WARNING: This uses a fixed, weak plaintext password. Use only in lab environments.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
import argparse

# === Fixed credentials (per request) ===
FIXED_USERNAME = "Customer"
FIXED_PASSWORD = "1234"
# =======================================

def run(cmd, check=True, capture_output=False, input_data=None):
    if isinstance(cmd, str):
        cmd = cmd.split()
    try:
        return subprocess.run(cmd, check=check, capture_output=capture_output, text=True, input=input_data)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {' '.join(cmd)}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        if check:
            sys.exit(1)
        return e

def ensure_root():
    if os.geteuid() != 0:
        print("This script must be run as root. Use sudo.")
        sys.exit(1)

def user_exists(username):
    res = subprocess.run(["getent", "passwd", username], capture_output=True, text=True)
    return res.returncode == 0

def create_user(username):
    if user_exists(username):
        print(f"[INFO] User '{username}' already exists. Skipping creation.")
        return
    print(f"[INFO] Creating user '{username}'.")
    run(["useradd", "-m", "-s", "/bin/bash", username])
    print(f"[OK] User '{username}' created.")

def set_password(username, password):
    pair = f"{username}:{password}\n"
    print(f"[INFO] Setting password for '{username}'.")
    # use chpasswd - normally reads "user:password" from stdin
    run(["chpasswd"], input_data=pair)
    print("[OK] Password set.")

def add_to_sudo(username):
    print(f"[INFO] Adding '{username}' to sudo group.")
    run(["usermod", "-aG", "sudo", username])
    print("[OK] Added to sudo group.")

def is_package_installed(pkgname):
    res = subprocess.run(["dpkg", "-s", pkgname], capture_output=True, text=True)
    return res.returncode == 0

def apt_install(packages):
    pkg_list = [p for p in packages if not is_package_installed(p)]
    if not pkg_list:
        print("[INFO] All packages already installed:", ", ".join(packages))
        return
    print("[INFO] Installing packages:", " ".join(pkg_list))
    run(["apt", "update"])
    run(["apt", "install", "-y"] + pkg_list)
    print("[OK] Installation complete.")

def systemctl_enable_start(service_name):
    print(f"[INFO] Enabling and starting {service_name} service.")
    run(["systemctl", "enable", "--now", service_name])
    # show status but don't fail on non-zero status
    run(["systemctl", "status", service_name], check=False)
    print(f"[OK] {service_name} enabled & started (status shown above).")

def backup_file(path: Path):
    ts = time.strftime("%Y%m%d-%H%M%S")
    bk = path.with_suffix(path.suffix + f".bak-{ts}")
    print(f"[INFO] Backing up {path} -> {bk}")
    shutil.copy2(path, bk)
    return bk

def permit_root_login_value(val):
    val = str(val).lower()
    # Accept common values, default to "no" otherwise
    if val in ("yes", "prohibit-password", "without-password", "forced-commands-only", "no"):
        return val
    return "no"

def ensure_sshd_password_auth(allow_passwords=True, permit_root_login="no"):
    conf = Path("/etc/ssh/sshd_config")
    if not conf.exists():
        print("[ERROR] /etc/ssh/sshd_config not found. Is OpenSSH installed?")
        sys.exit(1)
    backup_file(conf)

    text = conf.read_text()
    lines = text.splitlines()
    out_lines = []
    found_password = False
    found_root = False

    for ln in lines:
        striped = ln.strip()
        if striped.startswith("PasswordAuthentication"):
            out_lines.append(f"PasswordAuthentication {'yes' if allow_passwords else 'no'}")
            found_password = True
        elif striped.startswith("PermitEmptyPasswords"):
            out_lines.append("PermitEmptyPasswords no")
        elif striped.startswith("PermitRootLogin"):
            out_lines.append(f"PermitRootLogin {permit_root_login_value(permit_root_login)}")
            found_root = True
        else:
            out_lines.append(ln)

    if not found_password:
        out_lines.append(f"\n# Added by kali_add_ssh_user_fixed.py on {time.strftime('%Y-%m-%d %H:%M:%S')}")
        out_lines.append(f"PasswordAuthentication {'yes' if allow_passwords else 'no'}")
    if not found_root:
        out_lines.append(f"PermitRootLogin {permit_root_login_value(permit_root_login)}")

    new_text = "\n".join(out_lines) + "\n"
    conf.write_text(new_text)
    print("[OK] /etc/ssh/sshd_config updated (backup created).")

def restart_sshd():
    print("[INFO] Restarting sshd service.")
    run(["systemctl", "restart", "ssh"])
    print("[OK] sshd restarted.")

def ufw_allow_ssh():
    if shutil.which("ufw") is None:
        print("[INFO] ufw not installed - skipping firewall configuration.")
        return
    print("[INFO] Allowing SSH in UFW (ufw allow OpenSSH).")
    run(["ufw", "allow", "OpenSSH"], check=False)
    st = subprocess.run(["ufw", "status", "verbose"], capture_output=True, text=True)
    if "Status: active" in st.stdout:
        run(["ufw", "reload"], check=False)
        print("[OK] UFW reloaded.")
    else:
        print("[INFO] UFW is not active; rule added but ufw is inactive.")

def parse_args():
    p = argparse.ArgumentParser(description="Add fixed SSH user on Kali and enable password SSH login.")
    p.add_argument("--sudo", action="store_true", help="Add the user to sudo group")
    p.add_argument("--allow-ufw", action="store_true", help="Open SSH port in UFW (if installed)")
    p.add_argument("--install-fail2ban", action="store_true", help="Install fail2ban after setup (recommended)")
    return p.parse_args()

def main():
    ensure_root()
    args = parse_args()
    username = FIXED_USERNAME
    password = FIXED_PASSWORD

    create_user(username)
    set_password(username, password)

    if args.sudo:
        add_to_sudo(username)

    # Install OpenSSH server if needed
    apt_install(["openssh-server"])

    # Ensure password auth is enabled (per original request)
    ensure_sshd_password_auth(allow_passwords=True, permit_root_login="no")

    # Enable & start ssh
    systemctl_enable_start("ssh")

    # UFW handling
    if args.allow_ufw:
        ufw_allow_ssh()

    # Optional: fail2ban
    if args.install_fail2ban:
        apt_install(["fail2ban"])
        print("[INFO] fail2ban installed. You may want to configure /etc/fail2ban/jail.local")

    print("\nDone. Test by ssh'ing from another host:")
    print(f"  ssh {username}@<KALI_IP_OR_HOSTNAME>    (password: {password})")
    print("\nSECURITY NOTE: After testing, consider switching to SSH key auth and disabling passwords.")

if __name__ == "__main__":
    main()
