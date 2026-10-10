# Reading a USB / external disk over SSH on a non-root Astra Linux laptop

Proven 2026-08-13 against `<host>.example.test` (Astra,
domain user `user@example.test`, direct-reachable 192.0.2.10). Task:
"read data off a USB NVMe drive". This is the diagnostic + privilege sequence.

## 1. A USB NVMe shows as /dev/sdX, NOT nvme0n1
A USB-attached NVMe/SSD goes through a bridge chip (JMicron Tech, ASMedia,
Realtek RTL9210...) and enumerates as a SATA/SCSI block device, not an NVMe
device. The tell is the `TRAN` column in `lsblk`:

```bash
lsblk -o NAME,SIZE,TYPE,MODEL,TRAN,MOUNTPOINT
# sda  931.5G disk  Tech/JMicron Tech   usb    ← EXTERNAL disk (TRAN=usb)
# nvme0n1 ...                            nvme   ← internal system disk
```

`udisksctl status` shows both the bridge vendor (`JMicron Tech`) and the
internal NVMe model (`SAMSUNG MZVLB1T0HBLR...`) separately. Confirm with
`ls /dev/sd*` — the external disk is the only `sd*` device; the internal NVMe
stays on `/dev/nvme*`. `lsusb` may NOT show a mass-storage class if the bridge
enumerates oddly — rely on `/dev/sd*` + `lsblk`, not `lsusb`.

## 2. Check the partition filesystem BEFORE trying to mount
```bash
lsblk -f /dev/sda            # FSTYPE column: vfat / ext4 / LVM2_member / ...
```
If a partition is `LVM2_member` (very common on cloned/system disks), it is an
LVM PV that must be activated before the logical volumes are mountable. A
non-root user CANNOT do this: `vgscan`/`vgs`/`lvscan` are not even in a non-root
`$PATH` (need the full `/usr/sbin/vgs` AND root). You must activate the VG
(`vgchange -ay <vg>`) as root before any mount.

## 3. `udisksctl mount` fails over SSH — it needs a graphical polkit session
Expected exact failure:
```
Error creating textual authentication agent: Error opening current controlling
terminal for the process (`/dev/tty'): Нет такого устройства или адреса
GDBus.Error:org.freedesktop.UDisks2.Error.NotAuthorizedCanObtain: Not authorized
```
polkit's "active local session" is a logged-in DESKTOP, not your SSH session.
Do NOT retry `udisksctl` / `pkexec` over SSH — they will never authorize. This
is a hard wall, not a transient error.

## 4. Privilege reality on these domain laptops
- `user` has NO general sudo: `sudo -l` returns only
  `NOPASSWD: /usr/sbin/tlp, /usr/bin/sos, sosreport, astra-create-debug-logs`.
- Reading `/dev/sdX` needs group `disk` membership (the domain user is NOT in
  `disk` here) or root.
- A local admin account usually exists (`as`, uid 1000, group `astra-admin`)
  with a DIFFERENT password — `su - as` fails with the domain user's password.
- **Clean escalation to report to the user (don't brute-force):**
  1. get the local admin `as` password, OR
  2. one-time `sudo usermod -aG disk <user>` + grant `lvm2`/`mount` sudo (from `as`), OR
  3. have the user mount the disk locally on the desktop and read it there.

## 5. Scripted read-only probes: paramiko password login beats cmd.exe/plink
For directly-reachable hosts with a password, a paramiko script is the cleanest
multi-command probe: the password is a Python string (never a shell arg), so
special chars (`!@#$`, quotes, spaces) are immune to `cmd.exe /c` and git-bash
quoting. One `python probe.py` replaces N plink invocations — which matters on
flaky-WiFi laptops where each dropped session costs 5-30s.

```python
import paramiko
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect("192.0.2.10", 22, username="user",
          password="jhK0Zxq56!@#$", timeout=15,
          allow_agent=False, look_for_keys=False)  # key auth off: password only
def run(cmd, t=30):
    _,o,e = c.exec_command(cmd, timeout=t)
    return o.read().decode('utf-8','replace').strip(), e.read().decode('utf-8','replace').strip()
o,e = run("lsblk -o NAME,SIZE,TYPE,MODEL,TRAN,MOUNTPOINT")
print(o); c.close()
```

Gotchas:
- `allow_agent=False, look_for_keys=False` — force password auth, skip local keys.
- Domain user: the SSH username is the short form `user` (not
  `user@example.test`) — the FQDN is the IPA realm, not the SSH user.
- Wrap privileged reads in `echo <PW> | sudo -S ...` ONLY when the user actually
  has sudo; here `user` does not, so sudo returns "Sorry, user user is not
  allowed to execute ..." — that message is authoritative, don't chase it.
