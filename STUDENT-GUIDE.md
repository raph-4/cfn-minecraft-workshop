# Student Workshop Guide

## What you will do

This template is **deliberately broken**. Your job is to:

1. Fork this repo and create a branch
2. Run `cfn-lint` locally to find the bugs
3. Fix them
4. Push your branch and open a Pull Request
5. Watch the CI checks pass

---

## Part 1 — Fork and clone

1. Click **Fork** at the top-right of this page to copy the repo into your own GitHub account.

2. Clone your fork to your machine:

   ```bash
   git clone https://github.com/<your-username>/cfn-minecraft-workshop.git
   cd cfn-minecraft-workshop
   ```

---

## Part 2 — Create a branch

Never commit directly to `main`. Create a branch named after yourself or the fix:

```bash
git checkout -b fix/template-bugs
```

---

## Part 3 — Run the tests locally

Install `cfn-lint` (the CloudFormation linter):

```bash
pip install cfn-lint
```

Run the built-in checks **and** the custom rules in the `rules/` directory:

```bash
cfn-lint minecraft-server.yaml --append-rules rules/
```

You will see output like:

```
E9002  JavaMaxRam (2G) exceeds usable RAM for t4g.small ...   minecraft-server.yaml:90
E9003  Motd is still the default ("A Minecraft Server on AWS") ...   minecraft-server.yaml:111
W9001  AllowSshCidr is 0.0.0.0/0 ...   minecraft-server.yaml:136
```

cfn-lint exit codes:
| Code | Meaning |
|---|---|
| 0 | No issues |
| 2 | Errors found — **CI will fail** |
| 4 | Warnings only — CI passes but they are shown in the log |
| 6 | Both errors and warnings |

Lines starting with **E** are errors and will block the CI check. Lines starting with **W** are warnings — worth fixing but they won't block a merge.

---

## Part 4 — Fix the bugs

There are four things to fix. Three are caught by `cfn-lint`; the fourth only surfaces in the `sam validate` CI job.

### Bug 1 — `JavaMaxRam` is too high (E9002)

The default value for `JavaMaxRam` is set higher than the available RAM on the default instance type. The rule leaves 512 MB for the OS, so on a `t4g.small` (2 GB total) the maximum you can safely give to Java is **1536 M**.

Find the `JavaMaxRam` parameter and lower the default to a safe value.

<details>
<summary>Hint</summary>

```yaml
JavaMaxRam:
  Type: String
  Default: '1300M'   # safe for t4g.small (2 GB - 512 MB OS = 1536 MB usable)
```

</details>

---

### Bug 2 — `Motd` has not been changed from the default (E9003)

When players open the Minecraft multiplayer screen, the MOTD (Message of the Day) appears under your server's address. It currently reads **"A Minecraft Server on AWS"** — the default placeholder. Every student deploying this template would have the same server name, which is not very useful.

Find the `Motd` parameter and change the default to something that identifies your server.

<details>
<summary>Hint</summary>

```yaml
Motd:
  Type: String
  Default: 'My Workshop Server'   # change this to anything other than the default
```

</details>

---

### Bug 3 — `EIPAssociation` uses the wrong property

The `EIPAssociation` resource uses a property called `EIP`. That property was for **EC2-Classic**, which AWS retired in 2022. This template deploys into a **VPC**, so the correct property is `AllocationId`.

**The linter won't catch this one** — it is a silent bug that would only fail at deploy time when AWS rejects the request. This is intentional: not every infrastructure bug is detectable by static analysis, which is why code review and understanding the docs matter.

There is also a difference in how you reference it:

| Property | Value | When to use |
|---|---|---|
| `EIP` | `!Ref MinecraftEIP` → returns the IP address string | EC2-Classic (retired) |
| `AllocationId` | `!GetAtt MinecraftEIP.AllocationId` → returns the allocation ID | EC2-VPC |

Find the `EIPAssociation` resource and swap the property.

<details>
<summary>Hint</summary>

```yaml
EIPAssociation:
  Type: AWS::EC2::EIPAssociation
  Properties:
    InstanceId: !Ref MinecraftInstance
    AllocationId: !GetAtt MinecraftEIP.AllocationId
```

</details>

---

### Bug 4 — Circular dependency in `MinecraftSubnet` (SAM validate)

`MinecraftSubnet` has a `DependsOn: MinecraftInstance` attribute. But `MinecraftInstance` already references `MinecraftSubnet` via `!Ref` in its `NetworkInterfaces` — so each resource is waiting for the other to exist first. CloudFormation cannot resolve this and rejects the template.

`cfn-lint` does not always catch circular dependencies. **This bug only surfaces in the `SAM Validate` CI job**, which is why both checks exist.

The fix is to remove the `DependsOn: MinecraftInstance` line from `MinecraftSubnet` — the subnet has no real dependency on the instance and CloudFormation will figure out the correct creation order automatically from the `!Ref`.

<details>
<summary>Hint</summary>

```yaml
MinecraftSubnet:
  Type: AWS::EC2::Subnet
  # DependsOn: MinecraftInstance  <-- remove this line
  Properties:
    ...
```

</details>

---

## Part 5 — Optional: set a custom domain

The template has a `ServerDomain` parameter. If you own a domain name and want to point it at your server, set it here and the `ServerAddress` output will show the domain-based address instead of the raw IP. Leave it blank if you don't have one — the Elastic IP works fine.

If you do set it, make sure it's your real domain — the custom rule `W9003` will warn if it looks like a placeholder (e.g. `example.com`).

---

## Part 6 — Verify your fixes

Run the linter again after making your changes:

```bash
cfn-lint minecraft-server.yaml --append-rules rules/
```

Expected `cfn-lint` output after all four fixes:

```
W9001  AllowSshCidr is 0.0.0.0/0 ...   minecraft-server.yaml:138
```

Only the W9001 warning should remain. Exit code should be **4** (warnings only), not 2 or 6.

Also run SAM validate locally to check the circular dependency fix:

```bash
sam validate --template minecraft-server.yaml --region us-east-1
```

Expected output after the fix:

```
minecraft-server.yaml is a valid SAM Template
```

---

## Part 7 — Commit and push

Stage and commit your changes:

```bash
git add minecraft-server.yaml
git commit -m "fix: correct JavaMaxRam, Motd, and EIPAssociation"
git push -u origin fix/template-bugs
```

---

## Part 8 — Open a Pull Request

1. Go to your fork on GitHub
2. Click the **"Compare & pull request"** banner that appears after you push
3. Set the base repository to the **original** repo (not your fork) and base branch to `main`
4. Write a short description explaining what you changed and why
5. Click **Create pull request**

---

## Part 9 — Watch the CI checks

Once the PR is open, scroll down to the **Checks** section. Two workflows will run automatically:

| Workflow | What it does |
|---|---|
| `Validate CloudFormation Template` | Runs `cfn-lint` with built-in and custom rules |
| `SAM Validate CloudFormation Template` | Runs `sam validate` to check structure and syntax |

Both checks must show a green tick before the PR can be merged. If either fails, click **Details** to read the log, fix the issue, commit again to the same branch, and the checks will re-run automatically.

---

## Key concepts recap

| Concept | What it means |
|---|---|
| `!Ref` | Returns a resource's primary identifier (e.g. an IP address for an EIP) |
| `!GetAtt` | Returns a specific attribute of a resource (e.g. `AllocationId` for an EIP) |
| EC2-Classic vs VPC | EC2-Classic is retired — always use VPC properties for new templates |
| cfn-lint E vs W | E = error, blocks CI; W = warning, visible but non-blocking |
| CI on PRs | GitHub Actions runs every time you push, giving fast feedback on your changes |
