"""Run all discoverable project suites; retain failures without hiding them."""
import importlib.metadata
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT.parent/'handspeak-training'


def main():
    checks=[]
    for name,directory in [('project','training'),('accuracy','training/accuracy')]:
        command=[sys.executable,'-X','utf8','-m','unittest','discover','-s',directory,'-v']
        result=subprocess.run(command,cwd=ROOT,text=True,encoding='utf-8',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (CACHE/f'target20-{name}-tests-final.log').write_text(result.stdout,encoding='utf-8')
        count=re.search(r'Ran (\d+) tests?',result.stdout)
        failures=re.findall(r'^(?:FAIL|ERROR): (.+)$',result.stdout,re.M)
        checks.append(dict(name=name,passed=result.returncode==0,tests=int(count[1]) if count else None,failures=failures))
    for filename in ['app.js','beginner-recognition.js','guided-experience.js','target20-tracker.js','essential-words.js','vocabulary-library.js']:
        result=subprocess.run(['node','--input-type=module','--check'],input=(ROOT/filename).read_text(encoding='utf-8'),
                              text=True,encoding='utf-8',stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        checks.append(dict(name='syntax:'+filename,passed=result.returncode==0,error=result.stdout.strip()))
    versions={}
    for name in ['torch','numpy','mediapipe','scipy','scikit-learn','quickjs','remotezip']:
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]='not installed'
    report=dict(passed=all(c['passed'] for c in checks),checks=checks,dependencies=versions,
                scope='Automated software checks only; not webcam or recognition-accuracy proof')
    (CACHE/'target20-automated-checks-final.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':sys.exit(main())
