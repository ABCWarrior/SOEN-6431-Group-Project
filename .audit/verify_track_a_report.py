from pathlib import Path
import csv, hashlib, json, re
from datetime import datetime
root=Path(__file__).resolve().parents[1]
out=root/'track_a_analysis'
raw=out/'raw'
text=(out/'TRACK_A_REPORT.md').read_text()
expected=[
'Section 1: Technical Debt Inventory & Hotspot Analysis',
'Section 2: Methodology Log & Tool Screen Captures',
'Section 3: Comparative Evaluation Matrix',
'Section 4: Critical Audit & Hybrid Technical Debt Strategy',
'Section 5: Team Member Contributions']
assert re.findall(r'^## (.*)$',text,re.M)==expected
prose=re.sub(r'```.*?```','',text,flags=re.S)
assert len(re.findall(r'^# ',prose,re.M))==1
links=re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text)
for link in links:
    assert (out/link).exists(),link
assert not re.search(r'\{(?:TABLE|RUN_END|COVERAGE|SONAR_|COVERED|STATEMENTS|MISSING)',text)
run=json.loads((raw/'run_metadata.json').read_text())
assert run['exit_code']==0
assert run['script_sha256']==hashlib.sha256((out/'run_track_a.sh').read_bytes()).hexdigest()
original=json.loads((root/'.audit/track-a-before.json').read_text())
for f,sha in original.items():
    assert hashlib.sha256((root/f).read_bytes()).hexdigest()==sha,f
cov=json.loads((raw/'coverage.json').read_text())['totals']
assert (cov['covered_lines'],cov['num_statements'],cov['missing_lines'])==(3798,4187,389)
assert abs(cov['percent_covered']-90.70933842846907)<0.000001
assert '1019 passed, 5 skipped, 4 xfailed' in (raw/'pytest_coverage.txt').read_text()
rows=list(csv.DictReader((raw/'debt_summary_by_file.csv').open()))
assert len(rows)==78
assert [r['file'] for r in rows[:3]]==['httpie/core.py','httpie/cli/argparser.py','httpie/client.py']
radon=json.loads((raw/'radon_raw.json').read_text())
for r in rows[:10]:
    f=r['file']
    line=next(l for l in text.splitlines() if l.startswith('| ') and '`'+f+'`' in l and l.count('|')==9)
    cells=[x.strip() for x in line.strip('|').split('|')]
    assert cells[2]==f"{radon[f]['loc']:,}"
    assert cells[3]==f"{float(r['avg_ccn']):.1f}"
    assert cells[4]==str(int(float(r['max_ccn'])))
    assert cells[5]==str(int(float(r['violations'])))
    assert cells[6]==f"{float(r['coverage_pct']):.1f}%"
    assert cells[7]==f"{float(r['debt_score']):.1f}"
manifest=json.loads((raw/'screenshot_manifest.json').read_text())
assert len(manifest['views'])==6
start=datetime.fromisoformat(run['started_at']).timestamp()
end=datetime.fromisoformat(run['completed_at']).timestamp()
for view in manifest['views']:
    image=out/view['screenshot']
    assert image.read_bytes().startswith(b'\xff\xd8')
    assert view['screenshot_sha256']==hashlib.sha256(image.read_bytes()).hexdigest()
    assert datetime.fromisoformat(view['captured_at']).timestamp()>=end
    assert view['screenshot'] in text
    for src in view['sources']:
        file=out/src['path']
        assert src['sha256']==hashlib.sha256(file.read_bytes()).hexdigest()
        assert file.stat().st_mtime>=start,src['path']
sonar=json.loads((raw/'sonar_analysis_verification.json').read_text())
assert sonar['processing_success']
assert any('Executed task |' in l and 'status=SUCCESS' in l for l in sonar['server_log_lines'])
assert sonar['task_id'] in (raw/'sonar_scanner_log.txt').read_text()
secret=re.search(r'\b(sq[apu]_[A-Za-z0-9]+)',(out/'.env').read_text()).group(1)
for f in [out/'TRACK_A_REPORT.md',*raw.rglob('*.txt'),*raw.rglob('*.json')]:
    assert secret not in f.read_text(),f'Credential found in {f.name}'
assert 'Track B evidence is pending' in text
assert 'overall false-positive rate' in text
result={'formal_sections':5,'local_links_checked':len(links),'fresh_screenshots':6,'top_table_rows_checked':10,'pipeline_exit_code':0,'pytest_passed':1019,'coverage_percent':cov['percent_covered'],'sonar_processing_verified':True,'original_script_and_test_change_preserved':True,'credential_scan':'passed'}
(root/'.audit/track-a-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
