from __future__ import annotations
import argparse, json
from pathlib import Path
from src.evaluation.human_gold import adjudication_document_from_csv, build_human_gold as assemble, prepare_task_spec, readiness_failure, validate_annotation

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--tasks",type=Path,required=True); p.add_argument("--manifest",type=Path,default=Path("data/human_gold/split_manifest.json")); p.add_argument("--annotator-a",type=Path,required=True); p.add_argument("--annotator-b",type=Path,required=True); p.add_argument("--adjudication",type=Path,required=True); p.add_argument("--adjudicator-id"); p.add_argument("--completed-at"); p.add_argument("--output",type=Path,required=True); a=p.parse_args(argv)
    try:
        raw=json.loads(a.tasks.read_text(encoding="utf-8")); manifest=json.loads(a.manifest.read_text(encoding="utf-8")) if isinstance(raw,list) else None; tasks=prepare_task_spec(raw,manifest); left=validate_annotation(json.loads(a.annotator_a.read_text(encoding="utf-8-sig")),tasks,"A"); right=validate_annotation(json.loads(a.annotator_b.read_text(encoding="utf-8-sig")),tasks,"B")
        if a.adjudication.suffix.lower()==".csv":
            if not a.adjudicator_id or not a.completed_at: raise ValueError("裁决 CSV 必须提供 --adjudicator-id 和 --completed-at")
            adjudication=adjudication_document_from_csv(a.adjudication.read_text(encoding="utf-8-sig"),annotator_id=a.adjudicator_id,completed_at=a.completed_at,tasks=tasks)
        else: adjudication=json.loads(a.adjudication.read_text(encoding="utf-8-sig"))
        result=assemble(left,right,adjudication,tasks); code=0
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc: result,code=readiness_failure(str(exc)),1
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return code
if __name__=="__main__": raise SystemExit(main())
