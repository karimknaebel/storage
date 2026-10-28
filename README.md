# Storage

Publish `.tar.gz` release attachments through GitHub Pages.

- `surge.tar.gz` serves its contents at `https://karimknaebel.github.io/storage/surge/`.
- Each archive name uses the newest published release containing it; drafts and prereleases are ignored.
- Include files and directories directly in the archive, without an extra enclosing folder.
- Publishing or deleting a release rebuilds the site. You can also run **Actions → Publish assets → Run workflow**.

Upload archives to a draft release, then publish it. Release tags do not affect URLs. Deleting the newest copy falls back to an older release, if available.
