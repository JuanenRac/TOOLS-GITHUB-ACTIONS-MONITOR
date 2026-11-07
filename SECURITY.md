# Security Policy

## Reporting a vulnerability

Please report security problems privately to `electrohobby3d@gmail.com` (or with a private security advisory of this repository) and do not open a public issue.
Useful reports are: a way to reach the local web page from another machine, a way to make the monitor write outside its own folder, a way to read a token
or a private file through the page or the metrics endpoint, or an injection through a repository name, a workflow name or a log line.

## Design points you can rely on
- The web page and the optional metrics endpoint listen on `127.0.0.1` only, and refuse requests whose `Host` or `Origin` is not local.
- The monitor does not store or show tokens; it calls your own authenticated `gh` client.
- Everything that writes to GitHub is off by default and asks for a typed confirmation.
- The configuration page only writes a fixed list of keys, validated, after saving a backup copy.
