"""校验集成并生成 HACS 可直接安装的发布附件。"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import runpy
import zipfile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', help='发布标签，必须为 v + manifest 版本号')
    parser.add_argument('--check', action='store_true', help='只校验，不生成附件')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    integration = root / 'custom_components' / 'mcp_cocan'
    manifest = json.loads((integration / 'manifest.json').read_text())
    if args.tag and args.tag != f"v{manifest['version']}":
        raise ValueError('标签版本与 manifest.json 不一致')
    if manifest['domain'] != 'mcp_cocan':
        raise ValueError('集成 domain 不得改变')
    for source in integration.rglob('*.py'):
        ast.parse(source.read_text(), filename=str(source))
    for source in integration.rglob('*.json'):
        json.loads(source.read_text())
    defaults = runpy.run_path(str(integration / 'default_config.py'))
    entities = defaults['DEFAULT_ENTITIES_CONFIG']
    identities = [(item['type'], item['unique_id']) for item in entities]
    if len(identities) != len(set(identities)):
        raise ValueError('默认实体身份重复')
    for language in ('en', 'zh', 'zh-Hans'):
        data = json.loads((integration / 'translations' / f'{language}.json').read_text())
        for entity in entities:
            translated = data['entity'][entity['type']][entity['unique_id']]
            if not translated['name']:
                raise ValueError(f'{language} 存在空实体名')
            if entity['type'] == 'select':
                if set(translated['state']) != set(defaults['SELECT_OPTION_KEYS'][entity['unique_id']]):
                    raise ValueError(f'{language} 控制选项翻译不完整')
    print(f"校验通过：v{manifest['version']}，{len(entities)} 个实体，3 份完整翻译")
    if args.check:
        return
    output = root / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / 'mcp_cocan.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
        for source in sorted(integration.rglob('*')):
            if source.is_file() and '__pycache__' not in source.parts:
                # HACS zip_release 直接解压至集成目录，因此 ZIP 根层是 manifest.json。
                package.write(source, source.relative_to(integration))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / 'mcp_cocan.zip.sha256').write_text(f'{digest}  mcp_cocan.zip\n')
    print(f'已生成 {archive.name} 与 SHA256 校验文件')


if __name__ == '__main__':
    main()
