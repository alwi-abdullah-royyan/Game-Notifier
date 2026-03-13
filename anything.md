# Git account switching & persistent auth (quick reference)

Purpose: change which Git identity and authentication your repo uses, and choose a persistent method so you don't re-auth frequently.

1. See current identity and helper

```powershell
git config --list --show-origin
git config user.name
git config user.email
git config --global user.name
git config --global user.email
git config --get credential.helper
```

2. Set commit author (per-repo)

```powershell
# run inside the repo
git config user.name "Your Name"
git config user.email "you@example.com"
```

3. Set commit author globally (all repos)

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

4. HTTPS credential cache (Windows: Git Credential Manager)

- Enable GCM (Windows usually has it):

```powershell
git config --global credential.helper manager-core
# use per-repo credentials when needed:
git config --global credential.useHttpPath true
```

- After this, `git push` will prompt once; GCM stores tokens and refreshes them so you won't reauth every push.

- To remove cached HTTPS credentials (Windows GUI):
  - Open Windows Credential Manager → Windows Credentials → remove entries for `git:https://github.com` (or your host).

- CLI example (may require GCM Core):

```powershell
printf "protocol=https
host=github.com
" | git credential-manager-core erase
```

5. Recommended: SSH keys (no 90-day expiry by default)

- Generate a key per account:

Detailed SSH key setup (step-by-step)

- 1. Create `~/.ssh` if it doesn't exist

```powershell
New-Item -ItemType Directory -Force -Path $env:USERPROFILE\.ssh
```

- 2. Generate keys (choose one of the methods below)

PowerShell (Windows):

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\id_ed25519_personal -C "personal@example.com"
```

Git Bash / WSL / macOS / Linux:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_personal -C "personal@example.com"
```

- Notes when generating:
  - You will be prompted for a passphrase. A passphrase protects the private key; leave blank for no passphrase (less secure).
  - Use distinct filenames per account (e.g. `id_ed25519_personal`, `id_ed25519_work`).

- 3. Verify the files were created

```powershell
Get-ChildItem $env:USERPROFILE\.ssh\id_ed25519* -Force
```

- 4. File permissions
  - Unix (WSL/Git Bash/macOS):

  ```bash
  chmod 700 ~/.ssh
  chmod 600 ~/.ssh/id_ed25519_personal
  ```

  - Windows file permissions are managed by NTFS; avoid making the private key world-readable. Using `$env:USERPROFILE\.ssh` is correct.

- 5. Start ssh-agent and add the key

PowerShell (recommended on Windows):

```powershell
# enable + start agent (Admin may be required the first time)
Set-Service -Name ssh-agent -StartupType Automatic -ErrorAction SilentlyContinue
Start-Service ssh-agent
# add key to agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519_personal
# list loaded keys
ssh-add -l
```

Git Bash / WSL / macOS:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519_personal
ssh-add -l
```

- 6. Make agent persistent across sessions (Windows)
  - The OpenSSH Authentication Agent service (ssh-agent) set to `Automatic` will run at login and accept `ssh-add` calls. If keys are not automatically loaded on reboot, add `ssh-add` commands to your PowerShell profile or use a credential manager that integrates with the Windows keychain.

- 7. Create `~/.ssh/config` to select the right key per host/repo

```
Host github-personal
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_personal
  IdentitiesOnly yes

Host github-work
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_work
  IdentitiesOnly yes
```

- Example: switching a repo to use the personal key alias

```bash
git remote set-url origin git@github-personal:youruser/yourrepo.git
```

- 8. Copy public key and add to Git host

PowerShell:

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519_personal.pub | Set-Clipboard
```

macOS:

```bash
pbcopy < ~/.ssh/id_ed25519_personal.pub
```

Linux (xclip):

```bash
xclip -selection clipboard < ~/.ssh/id_ed25519_personal.pub
```

- 9. Test the SSH connection

```bash
ssh -T git@github.com
# or, if you used an alias
ssh -T git@github-personal
```

- 10. Troubleshooting tips
  - If `ssh-add` says file not found, re-check the path with `Get-ChildItem` / `ls`.
  - If `ssh -T` prompts for a password, the key wasn't used; check `ssh -vT git@github.com` to see which key(s) were offered.
  - Ensure `IdentityFile` paths in `~/.ssh/config` match the actual file locations (use full paths on Windows when necessary).

- Start agent and add keys:

```bash
# Windows PowerShell (Git Bash or WSL similar)
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519_personal
ssh-add ~/.ssh/id_ed25519_work
```

-- SSH files: where they live and how to upload the public key

- Key files location:
  - On Linux/macOS/WSL/Git Bash: `~/.ssh/` (e.g. `~/.ssh/id_ed25519_personal` and `~/.ssh/id_ed25519_personal.pub`).
  - On Windows PowerShell: `C:\Users\<YourUser>\.ssh\` (you can use `$env:USERPROFILE\\.ssh\\id_ed25519_personal`).

- The public key you upload is the `.pub` file (e.g. `id_ed25519_personal.pub`).

- Copy the public key to clipboard:
  - PowerShell (Windows):
    ```powershell
    Get-Content $env:USERPROFILE\.ssh\id_ed25519_personal.pub | Set-Clipboard
    ```
  - Command Prompt (Windows):
    ```cmd
    type %USERPROFILE%\.ssh\id_ed25519_personal.pub | clip
    ```
  - macOS:
    ```bash
    pbcopy < ~/.ssh/id_ed25519_personal.pub
    ```
  - Linux (with xclip):
    ```bash
    xclip -selection clipboard < ~/.ssh/id_ed25519_personal.pub
    ```

- Add the public key to your Git host (example: GitHub):
  1. Sign into GitHub, open **Settings → SSH and GPG keys → New SSH key**.
  2. Give it a descriptive title (e.g. "personal laptop") and paste the contents of the `.pub` file from your clipboard.
  3. Save.

- File permissions (Unix): ensure the private key is restricted:

  ```bash
  chmod 600 ~/.ssh/id_ed25519_personal
  ```

- Load key into agent (alternative PowerShell method):

  ```powershell
  # start SSH agent service (may require admin once)
  Start-Service ssh-agent
  # add key
  ssh-add $env:USERPROFILE\.ssh\id_ed25519_personal
  ```

- Create `~/.ssh/config` with host aliases:

```
Host github-personal
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_personal
  IdentitiesOnly yes

Host github-work
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_work
  IdentitiesOnly yes
```

- Use the alias in the remote URL for each repo:

```bash
# personal repo
git remote set-url origin git@github-personal:youruser/yourrepo.git
# work repo
git remote set-url origin git@github-work:workuser/workrepo.git
```

6. Per-repo identity with HTTPS + multiple accounts

- If you must use HTTPS and have different accounts on same host, set per-repo `user.name`/`user.email` and enable `credential.useHttpPath` so GCM stores separate credentials per repo path.

7. Notes and tradeoffs

- SSH: most seamless, keys don't expire unless you rotate them. Use ssh-agent to avoid entering passphrases every session.
- GCM/PAT: convenient for HTTPS; GCM uses refresh tokens so you won't need to reauth frequently. PATs may be policy-limited/expire.
- `credential.useHttpPath=true` is helpful when storing per-repo HTTPS credentials on the same host.

8. Quick troubleshooting

- Wrong author on commits? Fix author for past commits with `git commit --amend --author="Name <email>"` (single commit) or use `git filter-branch` / `git filter-repo` for history-wide changes.
- Still prompted for auth after enabling GCM: try clearing old credentials in Windows Credential Manager then push again to trigger GCM sign-in.

---

Keep this file somewhere safe and copy sections you need.
