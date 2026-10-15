#!/usr/bin/env python3
"""Generate case-sensitive default dictionaries and rule constants from a pinned wheel.

Identity entries are retained: a successful identity lookup must stop fallback
rules. Corrections are explicit source data, never transitive graph closure.
The extracted package is used only at generation/verification time.
"""
import argparse, hashlib, importlib.util, json, lzma, pathlib, struct, sys, tempfile, unicodedata, zipfile, tarfile, io
from generate_resources import WHEEL_SHA256, decode

LANGUAGES = ('de', 'fr', 'es', 'ru', 'nl')
DISTRIBUTION_NOTICES = (
    'NOTICES.txt', 'WRITTEN-OFFER.txt', 'LICENSE-PROVENANCE.json',
    'SIMPLEMMA-CODE-LICENSE.txt', 'SIMPLEMMA-UPSTREAM-DATA-LICENSES.txt',
    'ODbL-1.0.txt', 'CC-BY-4.0.txt', 'CC-BY-SA-3.0.txt',
    'CC-BY-SA-4.0.txt', 'FREELING-COPYING.txt', 'LGPL-LR.txt',
    'UD-SOURCE-NOTICES.txt', 'UD-FRENCH-PARTUT-LICENSE.txt',
    'UD-RUSSIAN-SYNTAGRUS-LICENSE.txt',
)

def encode(mapping, output):
    items = sorted((k.encode(), v.encode()) for k,v in mapping.items())
    blocks, offsets = bytearray(), []
    def varint(number):
        while number >= 128:
            blocks.append((number & 127) | 128); number >>= 7
        blocks.append(number)
    previous = b''
    for index,(key,value) in enumerate(items):
        if index%32 == 0: offsets.append(len(blocks)); previous=b''
        shared=0
        while shared<min(len(key),len(previous)) and key[shared]==previous[shared]:shared+=1
        varint(shared);varint(len(key)-shared);blocks.extend(key[shared:])
        shared=0
        while shared<min(len(key),len(value)) and key[shared]==value[shared]:shared+=1
        varint(shared);varint(len(value)-shared);blocks.extend(value[shared:]);previous=key
    base=16+4*len(offsets)
    output.write_bytes(b'SML2'+struct.pack('<III',32,len(offsets),len(items))+b''.join(struct.pack('<I',base+x) for x in offsets)+blocks)

def literal(value):
    # JSON string escapes overlap Swift except for control Unicode escapes.
    return json.dumps(value,ensure_ascii=False).replace('\\/', '/')

def generate_rules(path, version, resources):
    from simplemma.tokenizer import TOKREGEX
    from simplemma.strategies.defaultprefixes import DEFAULT_KNOWN_PREFIXES
    from simplemma.strategies.defaultrules.es import DEFAULT_RULES, _EXCLUDED
    from simplemma.strategies.clitic_decomposition import _CLITIC_SUFFIXES, PROCLITIC_LANGS
    # Python's word class includes L/N/underscore; ICU's \w includes additional
    # marks and join controls. Spell out the Python class for matching parity.
    pattern=TOKREGEX.pattern.replace(r'[^\W\d_]',r'[\p{L}\p{Nl}\p{No}]').replace(r'\w',r'[\p{L}\p{N}_]')
    lines=['// Generated from the verified Simplemma 2.0.0 wheel; do not edit.',
           'import Foundation','enum SimplemmaRuleData {',f'    static let normalizationVersion = {literal(version)}',f'    static let tokenizer = {literal(pattern)}',
           '    static let resources: [String: (entries: Int, bytes: Int, sha256: String)] = [']
    for lang in LANGUAGES:
        item=resources[lang]
        lines.append(f'        {literal(lang)}: ({item["entries"]}, {item["bytes"]}, {literal(item["sha256"])}),')
    lines+=['    ]', '    static let prefixes: [String: String] = [']
    for lang in LANGUAGES:
        if lang in DEFAULT_KNOWN_PREFIXES:lines.append(f'        {literal(lang)}: {literal(DEFAULT_KNOWN_PREFIXES[lang].pattern)},')
    lines+=['    ]','    static let spanishRules: [(String, String)] = [']
    for regex,replacement in DEFAULT_RULES.items():lines.append(f'        ({literal(regex.pattern)}, {literal(replacement)}),')
    lines+=['    ]',f'    static let spanishExcluded: Set<String> = [{", ".join(literal(x) for x in sorted(_EXCLUDED))}]',
            f'    static let spanishClitics = [{", ".join(literal(x) for x in _CLITIC_SUFFIXES["es"])}]',
            f'    static let frenchProclitics = [{", ".join(literal(x) for x in PROCLITIC_LANGS["fr"])}]','}']
    path.write_text('\n'.join(lines)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--wheel',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True)
    p.add_argument('--source-archive',type=pathlib.Path,help='Optional machine-readable corrected data archive for public distribution');p.add_argument('--rules-output',type=pathlib.Path,required=True);p.add_argument('--corrections',type=pathlib.Path,default=pathlib.Path(__file__).with_name('corrections.json'))
    args=p.parse_args()
    if hashlib.sha256(args.wheel.read_bytes()).hexdigest()!=WHEEL_SHA256:raise ValueError('Wheel checksum mismatch')
    corrections=json.loads(args.corrections.read_text())
    if set(corrections['corrections'])!=set(LANGUAGES):raise ValueError('Correction languages mismatch')
    args.output.mkdir(parents=True,exist_ok=True)
    if args.source_archive:
        # Fail before creating an archive if the publication would omit notices.
        for name in DISTRIBUTION_NOTICES:
            if not (args.output/name).is_file():raise ValueError(f'Missing distribution notice: {name}')
        license_provenance=json.loads((args.output/'LICENSE-PROVENANCE.json').read_text())
        if license_provenance['normalization_version']!=corrections['version']:raise ValueError('License notice version mismatch')
        for name, source in license_provenance['license_files'].items():
            if hashlib.sha256((args.output/name).read_bytes()).hexdigest()!=source['sha256']:raise ValueError(f'License checksum mismatch: {name}')
    report={'normalization_version':corrections['version'],'simplemma_version':'2.0.0','wheel_sha256':WHEEL_SHA256,'corrections_sha256':hashlib.sha256(args.corrections.read_bytes()).hexdigest(),'languages':{}}
    archive=tarfile.open(args.source_archive,'w:gz') if args.source_archive else None
    def add_source(name, content):
        if archive is not None:
            item=tarfile.TarInfo(name);item.size=len(content);item.mtime=0;item.mode=0o644
            archive.addfile(item,io.BytesIO(content))
    with zipfile.ZipFile(args.wheel) as wheel,tempfile.TemporaryDirectory() as tmp:
        wheel.extractall(tmp);sys.path.insert(0,tmp)
        for language in LANGUAGES:
            mapping=dict(decode(lzma.decompress(wheel.read(f'simplemma/strategies/dictionaries/data/{language}.plzma'))))
            for patch in corrections['corrections'][language]:
                for word in patch['forms']:mapping[word]=patch['lemma']
            if not all(unicodedata.normalize('NFC',w)==w and unicodedata.normalize('NFC',v)==v for w,v in mapping.items()):raise ValueError('Non-NFC dictionary data')
            if archive is not None:
                header=(f"# {language}: editable form/lemma data for {corrections['version']}\n"
                        f"# Modified by {license_provenance['modified_by']}; notice date {license_provenance['notice_date']}.\n"
                        "# Changes: explicit corrections in corrections.json; conversion from Simplemma 2.0.0.\n"
                        "# Original credits, copyright notices, licenses and warranty disclaimers: NOTICES.txt and accompanying license files.\n"
                        "# Underlying contents retain their applicable licenses; see LICENSE-PROVENANCE.json.\n")
                add_source(f'{language}.tsv', (header+''.join(f'{k}\t{v}\n' for k,v in sorted(mapping.items()))).encode())
            file=args.output/f'{language}.sml';encode(mapping,file)
            report['languages'][language]={'entries':len(mapping),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
        generate_rules(args.rules_output, corrections['version'], report['languages'])
    add_source('corrections.json',args.corrections.read_bytes())
    add_source('provenance.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    if archive is not None:
        for name in DISTRIBUTION_NOTICES:
            add_source(name,(args.output/name).read_bytes())
    if archive is not None:archive.close()
    (args.output/'provenance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'normalization_version':report['normalization_version'],'total_bytes':sum(r['bytes'] for r in report['languages'].values()),'languages':report['languages']}))

if __name__=='__main__':main()
