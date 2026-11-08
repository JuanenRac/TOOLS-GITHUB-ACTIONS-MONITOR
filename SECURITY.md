# Security Policy

## Reporting a vulnerability

Please report security problems privately to `electrohobby3d@gmail.com` (or with a private security advisory of this repository) and do not open a public issue.
Useful reports are: a way to reach the local web page from another machine, a way to make the monitor write outside its own folder, a way to read a token
or a private file through the page or the metrics endpoint, or an injection through a repository name, a workflow name or a log line.

## Design points you can rely on
- The web page and the optional metrics endpoint listen on `127.0.0.1` only, and refuse requests whose `Host` or `Origin` is not local. The optional network mode (off by default) adds an access token for every request, a list of accepted host names and a persistent warning.
- By default the monitor does not store or show tokens; it calls your own authenticated `gh` client. The optional token kept by the monitor lives in the secure store of the system and is never written to a setting, a log or an answer.
- Everything that writes to GitHub or runs a program is off by default, each action is confirmed on its own with a one-use token, and the AI assistant cannot start any of them.
- The configuration page only writes a fixed list of keys, validated, after saving a backup copy.
