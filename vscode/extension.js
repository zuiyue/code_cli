const vscode = require("vscode");
const path = require("path");

function activate(context) {
  const openTerminal = vscode.commands.registerCommand("aicoder.openTerminal", () => {
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath || ".";
    const terminal = vscode.window.createTerminal({
      name: "AI Coder",
      cwd: workspaceRoot,
      env: { DEEPSEEK_API_KEY: process.env.DEEPSEEK_API_KEY || "" },
    });
    terminal.show();
    terminal.sendText(`aicoder --project "${workspaceRoot}"`);
  });

  const openInExplorer = vscode.commands.registerCommand("aicoder.openInExplorer", () => {
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath || ".";
    const terminal = vscode.window.createTerminal({
      name: "AI Coder",
      cwd: workspaceRoot,
      env: { DEEPSEEK_API_KEY: process.env.DEEPSEEK_API_KEY || "" },
      location: vscode.TerminalLocation.Panel,
    });
    terminal.show();
    terminal.sendText(`aicoder --project "${workspaceRoot}"`);
  });

  context.subscriptions.push(openTerminal, openInExplorer);
}

function deactivate() {}

module.exports = { activate, deactivate };
