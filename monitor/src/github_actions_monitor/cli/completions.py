# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
"""`completions bash|zsh|fish|powershell`: the script that completes the commands, their words and their options, written from the real parser of the command line (never by hand, so it cannot fall
behind: a test compares what the script offers with what the parser accepts). The command only PRINTS the script; it writes nothing in your files. Put it where your shell reads completions
(docs/CLI_OPERATOR.md says where, for each shell).
"""
SHELLS = ("bash", "zsh", "fish", "powershell")
PROGRAM = "monitor_cli.py"


def describe(parser, by_command):
    """What the parser accepts: commands, options (with the choices of each one that has them) and the words each command takes. `by_command` maps a command to its words."""
    commands, options, choices = [], [], {}
    for action in parser._actions:      # noqa: SLF001 - the only way to ask argparse what it accepts
        if action.option_strings:
            for name in action.option_strings:
                if name.startswith("--"):
                    options.append(name)
                    if action.choices:
                        choices[name] = [str(c) for c in action.choices]
        elif action.dest == "command":
            commands = [str(c) for c in action.choices]
    return {"commands": commands, "options": sorted(set(options)), "choices": choices, "words": {k: list(v) for k, v in by_command.items()}}


def bash(info):
    cases = "".join(f'    {name}) COMPREPLY=($(compgen -W "{" ".join(values)}" -- "$cur")); return ;;\n' for name, values in sorted(info["choices"].items()))
    words = "".join(f'      {command}) COMPREPLY=($(compgen -W "{" ".join(values)}" -- "$cur")); return ;;\n' for command, values in sorted(info["words"].items()))
    return (f'# bash completion for {PROGRAM}: generated from its parser\n_monitor_cli() {{\n  local cur="${{COMP_WORDS[COMP_CWORD]}}" prev="${{COMP_WORDS[COMP_CWORD-1]}}"\n  COMPREPLY=()\n'
            f'  case "$prev" in\n{cases}  esac\n  if [[ "$cur" == -* ]]; then COMPREPLY=($(compgen -W "{" ".join(info["options"])}" -- "$cur")); return; fi\n'
            f'  if [[ $COMP_CWORD -eq 1 ]]; then COMPREPLY=($(compgen -W "{" ".join(info["commands"])}" -- "$cur")); return; fi\n'
            f'  case "${{COMP_WORDS[1]}}" in\n{words}  esac\n}}\ncomplete -F _monitor_cli {PROGRAM}\n')


def zsh(info):
    opts = "\n".join(f"    '{name}[{name[2:]}]{':value:(' + ' '.join(info['choices'][name]) + ')' if name in info['choices'] else ''}' \\" for name in info["options"])
    words = "".join(f"    {command}) _values 'word' {' '.join(values)} ;;\n" for command, values in sorted(info["words"].items()))
    return (f"#compdef {PROGRAM}\n# zsh completion for {PROGRAM}: generated from its parser\n_monitor_cli() {{\n  local -a commands\n  commands=({' '.join(info['commands'])})\n"
            f"  _arguments -s \\\n{opts}\n    '1:command:($commands)' \\\n    '*::word:->words'\n  case $state in\n  words)\n  case $words[1] in\n{words}  esac ;;\n  esac\n}}\n_monitor_cli \"$@\"\n")


def fish(info):
    lines = [f"# fish completion for {PROGRAM}: generated from its parser", f"complete -c {PROGRAM} -f", f"complete -c {PROGRAM} -n '__fish_use_subcommand' -a '{' '.join(info['commands'])}'"]
    for name in info["options"]:
        values = info["choices"].get(name)
        lines.append(f"complete -c {PROGRAM} -l {name[2:]}" + (f" -x -a '{' '.join(values)}'" if values else ""))
    for command, values in sorted(info["words"].items()):
        lines.append(f"complete -c {PROGRAM} -n '__fish_seen_subcommand_from {command}' -a '{' '.join(values)}'")
    return "\n".join(lines) + "\n"


def powershell(info):
    options = ", ".join(f"'{o}'" for o in info["options"])
    commands = ", ".join(f"'{c}'" for c in info["commands"])
    words = "\n".join(f"    '{command}' = @({', '.join(repr(v) for v in values)})" for command, values in sorted(info["words"].items()))
    choices = "\n".join(f"    '{name}' = @({', '.join(repr(v) for v in values)})" for name, values in sorted(info["choices"].items()))
    return (f"# PowerShell completion for {PROGRAM}: generated from its parser\n$MonitorCliOptions = @({options})\n$MonitorCliCommands = @({commands})\n$MonitorCliWords = @{{\n{words}\n}}\n$MonitorCliChoices = @{{\n{choices}\n}}\n"
            "Register-ArgumentCompleter -Native -CommandName 'monitor_cli.py','monitor_cli' -ScriptBlock {\n  param($wordToComplete, $commandAst, $cursorPosition)\n"
            "  $parts = @($commandAst.CommandElements | ForEach-Object { $_.ToString() })\n  $previous = if ($parts.Count -ge 2 -and $wordToComplete -eq '') { $parts[-1] } elseif ($parts.Count -ge 3) { $parts[-2] } else { '' }\n"
            "  $pool = if ($MonitorCliChoices.ContainsKey($previous)) { $MonitorCliChoices[$previous] } elseif ($wordToComplete -like '-*') { $MonitorCliOptions } else {\n"
            "    $command = $parts | Where-Object { $MonitorCliCommands -contains $_ } | Select-Object -First 1\n    if ($command -and $MonitorCliWords.ContainsKey($command)) { $MonitorCliWords[$command] } else { $MonitorCliCommands } }\n"
            "  $pool | Where-Object { $_ -like \"$wordToComplete*\" } | ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }\n}\n")


def script(shell, parser, by_command):
    info = describe(parser, by_command)
    return {"bash": bash, "zsh": zsh, "fish": fish, "powershell": powershell}[shell](info)
