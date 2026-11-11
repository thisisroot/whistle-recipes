# whistle-recipes

Recipes for running apps on an OS they weren't built for, used by
[Whistle](https://github.com/thisisroot/whistle). For example, a Windows app on
Linux through Wine, or a Linux app on Windows through WSL.

A recipe says where the installer comes from, which typed steps prepare the
environment, and which programs to add to the menu. There is no shell step:
recipes can only use the actions in the schema, so they're easy to review and
can't run arbitrary commands.

## Example

```yaml
# recipes/org.notepad-plus-plus.NotepadPlusPlus.yaml
schema_version: 1
id: org.notepad-plus-plus.NotepadPlusPlus
app: org.notepad-plus-plus.NotepadPlusPlus
version_range: "8.9"
runtime: wine
requires:
  wine: ">=8.0"
  arch: win64
installer:
  type: download
  url: https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.9.9/npp.8.9.9.Installer.x64.exe
  sha256: "a18cfb33d616c8eecda0059604d40bdb9d607fbc4ede857c8be6e41986464367"
steps:
  - run_installer: { args: ["/S"] }
launchers:
  - name: Notepad++
    exe: 'C:\Program Files\Notepad++\notepad++.exe'
    mime: [text/plain]
```

## The format

The full definition is [`recipe.schema.json`](src/whistle_recipes/recipe.schema.json).
In short:

- **runtime**: `wine`, `proton`, `wsl` or `vm`.
- **installer**: one of
  - `download`: an HTTPS URL on the vendor's own site, plus its SHA-256.
  - `user_supplied`: the user picks the file, which must match one of the listed
    hashes. Use this for licensed software that can't be downloaded freely.
  - `package`: a package inside the runtime, such as apt inside WSL.
- **steps**: `winetricks`, `dll_override`, `registry`, `copy`, `env` and
  `run_installer`, in order.
- **launchers**: the programs to add to the menu, with optional MIME types and categories.
- **health_check**: which launcher must open a window after install.
  **fallback** says what to offer if it doesn't.

## Adding a recipe

1. Create `recipes/<id>.yaml`. The file name must match `id`.
2. Get the installer's SHA-256 from a source you trust: the vendor's published
   checksums, or GitHub's asset digest. Don't just hash whatever you happened
   to download.
3. Validate it:

   ```sh
   uv sync
   uv run whistle-recipes-validate recipes
   uv run pytest
   ```

4. Open a pull request.

The app must exist in the Whistle catalog. New recipes start as `draft`, and
clients only offer drafts with `--allow-draft`. A maintainer promotes a recipe
to `community` or `verified` in
[whistle-server](https://github.com/thisisroot/whistle-server)'s `seed/recipe-status.json`.

## How recipes reach users

whistle-server indexes this repo whenever it rebuilds the catalog. It stores
each change as a new revision, so compatibility reports always refer to the
exact steps someone ran. The current revision goes into the index that
`whistle update` downloads.

This repo is also a Python package (`whistle_recipes`) that provides the schema
and the validator, and whistle-server uses it to check recipes.

## License

CC0-1.0. Recipes are facts about how to install software, so anyone can reuse them.
