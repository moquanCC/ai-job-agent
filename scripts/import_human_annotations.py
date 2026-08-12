from __future__ import annotations
import argparse, json
from pathlib import Path
from src.evaluation.human_gold import annotation_document_from_csv, prepare_task_spec, readiness_failure, validate_annotation

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--tasks",type=Path,required=True); p.add_argument("--manifest",type=Path,default=Path("data/human_gold/split_manifest.json")); p.add_argument("--input",type=Path,required=True); p.add_argument("--role",choices=("A","B"),required=True); p.add_argument("--annotator-id"); p.add_argument("--completed-at"); p.add_argument("--output",type=Path,required=True); a=p.parse_args(argv)
    try:
        raw=json.loads(a.tasks.read_text(encoding="utf-8")); manifest=json.loads(a.manifest.read_text(encoding="utf-8")) if isinstance(raw,list) else None; tasks=prepare_task_spec(raw,manifest)
        if a.input.suffix.lower()==".csv":
            if not a.annotator_id or not a.completed_at: raise ValueError("CSV 导入必须提供 --annotator-id 和 --completed-at")
            document=annotation_document_from_csv(a.input.read_text(encoding="utf-8-sig"),annotator_id=a.annotator_id,role=a.role,completed_at=a.completed_at,tasks=tasks)
        else: document=json.loads(a.input.read_text(encoding="utf-8-sig"))
        result=validate_annotation(document,tasks,a.role); result={"human_gold":False,"status":"validated_single_annotation","task_fingerprint":tasks["task_fingerprint"],"pair_fingerprint":tasks["pair_fingerprint"],**result}; code=0
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc: result,code=readiness_failure(str(exc)),1
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return code
if __name__=="__main__": raise SystemExit(main())
