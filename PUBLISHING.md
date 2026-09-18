# Publishing SIA to the VS Code Marketplace & Open VSX

This guide explains how to publish the **SIA Extension** (`sia-vscode-extension`) to the **VS Code Marketplace** so users can search for and install `sia-vscode-extension` directly inside VS Code, Cursor, Windsurf, and Kiro.

---

## Part 1: VS Code Marketplace (Official Microsoft Store)

### Step 1: Create a Publisher Account
1. Go to the [VS Code Marketplace Publisher Management](https://marketplace.visualstudio.com/manage) page.
2. Sign in with your Microsoft/GitHub account.
3. Click **Create publisher** and enter your Publisher ID (e.g. `GunjanGrunge`).
4. Make sure `"publisher": "GunjanGrunge"` in `extension/package.json` matches your publisher ID.

### Step 2: Create an Azure DevOps Personal Access Token (PAT)
1. Go to [dev.azure.com](https://dev.azure.com) and log in.
2. Click your User Settings icon (top right) -> **Personal access tokens**.
3. Click **+ New Token**.
4. Set Organization to **All accessible organizations**.
5. Set Expiration to **1 year**.
6. Under Scopes, select **Custom defined** -> scroll down to **Marketplace** -> check **Manage**.
7. Click **Create** and copy your Personal Access Token.

### Step 3: Login & Publish via `vsce`
Run the following commands in terminal:

```bash
# 1. Login with your publisher ID
npx @vscode/vsce login GunjanGrunge
# Paste your Personal Access Token when prompted

# 2. Publish to VS Code Marketplace
cd extension
npx @vscode/vsce publish
```

Once published, your extension will be searchable in VS Code extensions search (`Ctrl+Shift+X`) within ~5 minutes!

---

## Part 2: Open VSX Registry (For Cursor, VSCodium, Kiro, etc.)

Open VSX ([open-vsx.org](https://open-vsx.org/)) is the open extension registry used by **Cursor**, **VSCodium**, **Kiro**, and other open IDEs.

1. Go to [open-vsx.org](https://open-vsx.org/) and log in with GitHub.
2. Go to **Settings -> Access Tokens** and generate a token.
3. Publish your built `.vsix` file:

```bash
npx ovsx publish extension/sia-vscode-extension-0.2.0.vsix -t <YOUR_OPEN_VSX_TOKEN>
```
