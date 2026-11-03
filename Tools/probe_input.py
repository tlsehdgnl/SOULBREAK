#!/usr/bin/env python3
"""Measure action transitions under identical Enhanced Input key presses in a Mac Development build."""
import argparse
import hashlib
import json
import plistlib
import re
import subprocess
from pathlib import Path

CASES = (
    ('early_second_click', 'LeftMouseButton', .20, 'ReturnCut'),
    ('buffered_dodge', 'SpaceBar', .25, 'Evade'),
    ('late_parry', 'RightMouseButton', .45, 'Parry'),
)


def run_case(executable, project, output, fps, name, key, delay, action):
    def frames(seconds):
        return int(seconds * fps + .5)

    first = frames(.35)
    follow = first + frames(delay)
    end = frames(1.66)
    expected = {'ReturnCut': first + frames(.60), 'Evade': first + frames(.32), 'Parry': follow}[action]
    # Observe every simulation tick at the expected change and also sample the whole move.
    # Limiting the number of commands keeps ExecCmds within UE's startup command buffer.
    samples = sorted(set(range(first - 1, end + 1, 5)) | set(range(first - 1, first + 5)) |
                     set(range(follow - 1, follow + 4)) | set(range(expected - 2, expected + 5)) | {end})
    keys = [(first, 'Input.+key LeftMouseButton 1'), (first + 1, 'Input.-key LeftMouseButton'),
            (follow, f'Input.+key {key} 1'), (follow + 1, f'Input.-key {key}')]
    commands = keys + [(i, 'getall SBHero Action') for i in samples] + [(frames(1.75), 'quit')]
    script = ','.join('defer ' * i + cmd for i, cmd in sorted(commands, key=lambda item: item[0]))
    if len(script) > 15000:
        raise ValueError('Command line would exceed the engine startup buffer')
    args = [str(executable)]
    if project:
        args += [str(project), '/Game/SoulBreak/Maps/L_Cathedral', '-game']
    args += ['-unattended', '-NullRHI', '-nosound', '-benchmark', '-NoSplash', '-UseFixedTimeStep',
             f'-FPS={fps}', '-FullStdOutLogOutput', '-stdout', '-ExecCmds=' + script]
    log = output / f'{name}-{fps}.log'
    with log.open('w') as stream:
        subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, timeout=100, check=True)
    samples_read = re.findall(r'BP_Hero_C_\d+\.Action\s*=\s*(?:ESBHeroAction::)?(\w+)', log.read_text(errors='replace'))
    if len(samples_read) != len(samples):
        raise RuntimeError(f'Incomplete action readings; inspect {log}')
    by_frame = dict(zip(samples, samples_read))
    first_cut = next((i for i, value in by_frame.items() if value == 'Cut'), None)
    if first_cut is None:
        raise RuntimeError(f'First attack input did not execute; inspect {log}')
    observed = next((i for i, value in by_frame.items() if value == action), None)
    if observed is not None and observed - 1 not in by_frame:
        raise RuntimeError(f'Expected consecutive samples around the change; inspect {log}')
    return {
        'case': name, 'fixed_fps': fps, 'attack_press_frame': first, 'cut_observed_frame': first_cut,
        'followup_press_frame': follow, 'followup_observed_frame': observed,
        'press_to_observed_sim_ms': None if observed is None else round(1000 * (observed - follow) / fps, 3),
        'observed_until_frame': end,
    }


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path, help='Mac Development .app or its executable')
    parser.add_argument('output', type=Path)
    parser.add_argument('--project', type=Path, help='When running an editor executable in game mode')
    parser.add_argument('--fps', nargs='+', type=int, choices=(30, 60), default=[30, 60])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    executable = args.game.resolve()
    if executable.suffix == '.app':
        with (executable / 'Contents/Info.plist').open('rb') as plist:
            executable = executable / 'Contents/MacOS' / plistlib.load(plist)['CFBundleExecutable']
    project = args.project.resolve() if args.project else None
    source = project.parent / 'Binaries/Mac/libUnrealEditor-SoulBreak.dylib' if project else executable
    digest = sha256(source)
    rows = [run_case(executable, project, args.output, fps, *case) for fps in args.fps for case in CASES]
    if sha256(source) != digest:
        raise RuntimeError('Executable or project module changed during the measurement')
    report = {
        'method': 'Standalone NullRHI; forced press/release events use the regular Enhanced Input mappings. '
                  'Times count fixed simulation frames until the first property observation of the action. '
                  'This includes command/query scheduling and excludes physical mouse, rendering and display latency.',
        'runtime': 'editor -game' if project else 'packaged Development', 'code_sha256': digest, 'cases': rows,
    }
    path = args.output / 'timings.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(path)


if __name__ == '__main__':
    main()
