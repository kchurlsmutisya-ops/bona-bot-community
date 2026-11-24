# Bona Bot Community Edition

A clean-room, user-supervised coding assistant based on the feature categories
identified during static analysis of a user-provided Bona Bot executable. This
is a new implementation, not recovered source code and not an exact
reconstruction.

The inspected executable was a PyInstaller bundle containing Python 3.14 and
PySide6 modules for a Gemini coding agent, workspace operations, VS Code
integration, and account/licensing features. Static inspection does not prove
runtime behavior. The original executable was not run.

## What this edition does

- Sends a user-written prompt to the Gemini API using an API key entered for the
  current app session.
- Optionally attaches one file that the user selects from a chosen workspace.
  The file content is sent to Google once with the next **Send** action.
- Shows the generated response. The user can save it as a new file under the
  chosen workspace after reviewing it. Attached file contents are not retained
  in the local chat history after that request.
- Keeps the API key and conversation in memory only; it does not persist them.

This edition does not scan workspaces, modify existing files, delete files,
execute commands, automate VS Code typing, or implement the original
account/license/payment/admin services. It is intentionally not an autonomous
agent.

## Run

Requires Python 3.10 or later with Tkinter available.

```powershell
$env:PYTHONPATH = "src"
python -m bona_bot
```

Run from this directory. Alternatively, install the project with
`python -m pip install .` and then use `bona-bot`.

## Build a Windows executable

On Windows, install the optional packager and run the build script:

```powershell
python -m pip install ".[build]"
.\scripts\build-windows.ps1
```

The script creates `dist\BonaBot.exe` as a single-file, windowed application.
The executable is not signed; do not distribute it as an official release
without reviewing and signing the build.

## Privacy and safety

- Use an API key you are authorized to use. It is sent in the
  `X-Goog-Api-Key` request header and is not written to disk by this app.
- Only the file explicitly selected by the user is read. Review it before
  sending; selected file content is transmitted to Google's Gemini API.
- Responses are never applied automatically. Saving creates a new file and
  refuses to overwrite an existing path.
- No local command execution or VS Code UI automation is provided.

## Development

Run the focused tests with:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## License

MIT. See [LICENSE](LICENSE).
