"""Build, test and package Soul Break using the locally installed UE 5.8.4 toolchain."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

project = Path(__file__).resolve().parents[1]
uproject = project / 'SoulBreak.uproject'
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build','test','package','shipping'))
    parser.add_argument('--engine', default=os.environ.get('UE_ROOT'), help='UE 5.8.4 installation folder')
    args = parser.parse_args()
    host = platform.system()
    if host not in ('Windows','Darwin'):
        parser.error('Run on Windows or macOS using the native target toolchain.')
    mac = host == 'Darwin'
    target = 'Mac' if mac else 'Win64'
    default = '/Users/Shared/Epic Games/UE_5.8' if mac else str(Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Epic Games/UE_5.8')
    engine = Path(args.engine or default) / 'Engine'
    with (engine/'Build/Build.version').open(encoding='utf-8-sig') as f:
        info = json.load(f)
    if tuple(info[key] for key in ('MajorVersion','MinorVersion','PatchVersion')) != (5,8,4):
        parser.error('Choose the same UE 5.8.4 installation on both computers (--engine or UE_ROOT).')
    batch = engine/'Build/BatchFiles'
    build = batch/('Mac/Build.sh' if mac else 'Build.bat')
    uat = batch/('RunUAT.sh' if mac else 'RunUAT.bat')
    cmd = engine/'Binaries'/target/('UnrealEditor-Cmd' if mac else 'UnrealEditor-Cmd.exe')
    def run(*argv):
        subprocess.run(list(map(str,argv)), cwd=project, check=True)
    if args.action in ('build','test'):
        run(build,'SoulBreakEditor',target,'Development',uproject,'-NoHotReload')
    if args.action == 'test':
        reports = project/'Saved'/'QA'
        reports.mkdir(parents=True,exist_ok=True)
        report = Path(tempfile.mkdtemp(prefix='unit-',dir=reports))
        run(cmd,uproject,'-unattended','-NullRHI','-nosound','-nop4','-ExecCmds=Automation RunTests SoulBreak.',
            '-TestExit=Automation Test Queue Empty',f'-ReportExportPath={report}')
        with (report/'index.json').open(encoding='utf-8-sig') as f:
            results = json.load(f)
        required = {'SoulBreak.Combat.Dedup','SoulBreak.Combat.WindowsAndResources',
                    'SoulBreak.Boss.BreakOnce','SoulBreak.Boss.DeathPriority'}
        passed = {test['fullTestPath'] for test in results['tests'] if test['state']=='Success'}
        print(f'Automation report: {report}')
        if not required.issubset(passed) or results.get('failed') or results.get('notRun'):
            return 1
    elif args.action in ('package','shipping'):
        config = 'Shipping' if args.action=='shipping' else 'Development'
        run(uat,'BuildCookRun',f'-project={uproject}',f'-platform={target}',f'-clientconfig={config}',
            '-build','-cook','-stage','-pak','-archive','-unattended','-nop4',
            f'-archivedirectory={project/"Builds"/config}')
        if mac:
            # UE 5.8.4 can archive the link output without the staged Contents/UE payload.
            app = Path('SoulBreak-Mac-Shipping.app' if config == 'Shipping' else 'SoulBreak.app')
            stage = project/'Saved/StagedBuilds/Mac'/app
            output = project/'Builds'/config/'Mac'
            if not any((stage/'Contents/UE').rglob('*.utoc')):
                raise RuntimeError('Missing cooked IoStore container in staged Mac app')
            output.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='soulbreak-archive-',dir=output) as tmp:
                complete = Path(tmp)/app
                previous = Path(tmp)/'previous.app'
                run('ditto',stage,complete)
                run('codesign','--verify','--deep','--strict',complete)
                destination = output/app
                if destination.exists():
                    destination.rename(previous)
                try:
                    complete.rename(destination)
                except OSError:
                    if previous.exists():
                        previous.rename(destination)
                    raise
    return 0
if __name__=='__main__':
    sys.exit(main())
