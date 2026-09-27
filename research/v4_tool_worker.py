"""Single tool invocation in a child process; all outputs stay in its attempt directory."""
import argparse
import json
import os
import time
from pathlib import Path

from agent.tools import execute_tool
from research.io import write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--reply', required=True)
    parser.add_argument('--ready', required=True)
    parser.add_argument('--fault', choices=('none', 'timeout', 'partial_write'),
                        default='none')
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text(encoding='utf-8'))
    ready = Path(args.ready)
    ready.write_text('ready\n', encoding='utf-8')
    if args.fault == 'timeout':
        time.sleep(3600)
    if args.fault == 'partial_write':
        target = Path(request['args']['artifact_dir']) / 'table.csv'
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('wb') as stream:
            stream.write(b'incomplete,header\n1,')
            stream.flush()
            os.fsync(stream.fileno())
        time.sleep(3600)
    result = execute_tool(request['action'], request['args'])
    temp = Path(args.reply).with_suffix('.tmp')
    write_json(temp, result)
    os.replace(temp, args.reply)


if __name__ == '__main__':
    main()
