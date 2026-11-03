#!/usr/bin/env python3
"""Capture a Development Mac or Windows build. Demo runs at fixed 24 Hz and performance uses real time."""
import argparse
import csv
import plistlib
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path


def encode_capture(output, encoder):
    frames = sorted((output / 'Frames').glob('frame_*.png'))
    if len(frames) < 60 * 24:
        raise RuntimeError(f'Incomplete demo: only {len(frames)} frames')
    for index, frame in enumerate(frames):
        if frame.name != f'frame_{index:05d}.png':
            raise RuntimeError(f'Missing frame {index}')
    command = [encoder, '-hide_banner', '-loglevel', 'warning', '-y', '-framerate', '24',
               '-i', str(output / 'Frames' / 'frame_%05d.png')]
    audio = output / 'game.wav'
    if audio.is_file() and audio.stat().st_size > 1024:
        command.extend(['-i', str(audio), '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '160k'])
    else:
        print('Master audio capture is unavailable.', file=sys.stderr)
    command.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', '-t', f'{len(frames)/24:.3f}', str(output / 'SoulBreak-Demo.mp4')])
    subprocess.run(command, check=True)
    with (output / 'events.csv').open(encoding='utf8') as stream:
        events = list(csv.DictReader(stream))
    for name in ('engaged', 'parry', 'armbreak', 'stomp', 'victory', 'defeat'):
        mark = next((entry for entry in events if entry['event'] == name), None)
        if mark:
            offset = {'parry': 2, 'armbreak': 4, 'victory': 18, 'defeat': 18}.get(name, 0)
            shutil.copyfile(frames[min(int(mark['frame'])+offset,len(frames)-1)], output/f'{name}.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('demo', 'perf', 'stills', 'encode'))
    parser.add_argument('game', type=Path, help='Mac app bundle, its executable, or the packaged Win64 game executable')
    parser.add_argument('output', type=Path, help='New directory for logs, frame samples or video')
    parser.add_argument('--ffmpeg', help='FFmpeg executable; required for video encoding')
    args = parser.parse_args()
    output = args.output.resolve()
    encoder = args.ffmpeg or shutil.which('ffmpeg')
    if args.mode in ('encode','demo') and not encoder:
        parser.error('Provide --ffmpeg with the path to FFmpeg')
    if args.mode == 'encode':
        encode_capture(output, encoder)
        return
    if output.exists() and any(output.iterdir()):
        parser.error('Use an empty output directory to keep independent runs separate')
    output.mkdir(parents=True,exist_ok=True)
    game = args.game.resolve()
    bundle = game if game.suffix == '.app' else next((p for p in game.parents if p.suffix=='.app'),None)
    if bundle:
        with (bundle / 'Contents/Info.plist').open('rb') as plist:
            metadata = plistlib.load(plist)
        game = bundle / 'Contents/MacOS' / metadata['CFBundleExecutable']
        # A sandboxed Mac app can record inside its own container.
        cache = Path.home() / 'Library/Containers' / metadata['CFBundleIdentifier'] / 'Data/Library/Caches/SoulBreakReview'
    elif game.suffix.lower() == '.exe' and game.is_file():
        cache = Path(tempfile.gettempdir()) / 'SoulBreakReview'
    else:
        parser.error('Select a packaged Development .app or Win64 .exe')
    cache.mkdir(parents=True,exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=args.mode+'-',dir=cache))
    print(f'Capturing into {work}',flush=True)
    command = [str(game), '-windowed', '-RenderOffscreen', '-ForceRes', '-unattended', '-NoSplash',
               '-NoVSync', '-NoScreenMessages', '-stdout', f'-SBOut={work}', f'-abslog={work}/game.log']
    if args.mode == 'perf':
        command.extend(['-SBPerf', '-ResX=1920', '-ResY=1080', '-ExecCmds=r.ScreenPercentage 100',
                        '-trace=cpu,frame,gpu,bookmark', f'-tracefile={work}/phase2.utrace'])
    else:
        command.extend(['-SBDemo', '-UseFixedTimeStep', '-fps=24', '-ResX=1280', '-ResY=720',
                        '-deterministicaudio', '-ini:Engine:[Audio]:UnfocusedVolumeMultiplier=1.0'])
        if args.mode == 'demo':
            command.append('-SBVideoFrames')
    with (work / 'process.log').open('w') as log:
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    # A trace can finish flushing before a shutdown fault. Export complete samples
    # for diagnosis and still return a failing status for that process.
    if process.returncode and args.mode != 'perf':
        raise RuntimeError(f'Capture exited with {process.returncode}. Logs and partial files are in {work}.')
    if args.mode == 'demo':
        encode_capture(work, encoder)
    elif args.mode == 'perf':
        with (work / 'summary.csv').open('r',encoding='utf8') as stream:
            runs=list(csv.DictReader(stream))
        if len(runs)!=3 or any(float(sample['seconds'])<60 for sample in runs):
            raise RuntimeError('Three complete 60-second samples were not produced')
    for file in work.iterdir():
        if file.is_file() and file.name != 'game.wav':
            shutil.move(str(file), str(output / file.name))
    shutil.rmtree(work)
    print(output)
    if process.returncode:
        raise RuntimeError(f'Performance samples exported to {output}, but the game exited with {process.returncode}.')


if __name__=='__main__':
    main()
