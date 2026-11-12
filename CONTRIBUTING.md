# Contributing to whistle-recipes

The general guide, including commit sign-off, is in the
[whistle repo's CONTRIBUTING.md](https://github.com/thisisroot/whistle/blob/main/CONTRIBUTING.md).
How to write a recipe is in the [README](README.md#adding-a-recipe).

## Checklist for a new recipe

- [ ] The file is `recipes/<id>.yaml`, and the app exists in the Whistle catalog.
- [ ] The installer comes from the vendor's own site over HTTPS.
- [ ] The SHA-256 comes from a source you trust: the vendor's published
      checksums, or GitHub's asset digest.
- [ ] `uv run whistle-recipes-validate recipes` and `uv run pytest` pass.
- [ ] You installed and launched the app with
      `whistle install <app> --via wine --allow-draft`, and said in the pull
      request which Wine version and distro you used.
- [ ] The steps are the minimum the app needs. Every winetricks verb and
      registry change has a reason, written as a comment.

New recipes start as `draft`. A maintainer promotes them in whistle-server.

## License

Recipes are CC0-1.0. By contributing, you dedicate your recipe to the public domain.
