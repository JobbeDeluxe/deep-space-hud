Option Explicit
Dim shell, files, root, runner, command, result
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
runner = files.BuildPath(root, ".venv\Scripts\pythonw.exe")
If files.FileExists(runner) Then
    command = """" & runner & """ """ & files.BuildPath(root, "launch.pyw") & """"
Else
    command = "pyw.exe -3 """ & files.BuildPath(root, "launch.pyw") & """"
End If
On Error Resume Next
result = shell.Run(command, 0, False)
If Err.Number <> 0 Then
    Err.Clear
    result = shell.Run("pythonw.exe """ & files.BuildPath(root, "launch.pyw") & """", 0, False)
    If Err.Number <> 0 Then
        MsgBox "Python wurde nicht gefunden. Bitte einmal START.cmd ausfuehren, um die Einrichtung zu pruefen.", 16, "Deep Space HUD"
    End If
End If
