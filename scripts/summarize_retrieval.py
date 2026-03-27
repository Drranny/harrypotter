#!/usr/bin/env python3
"""
8개의 검색 평가 JSON 파일에서 핵심 지표를 추출하여 마크다운 표로 출력합니다.
"""

import glob
import json
import os

def main():
    # results 폴더 안의 eval_ 로 시작하는 모든 json 파일 찾기
    files = sorted(glob.glob("results/eval_*.json"))
    
    if not files:
        print("JSON 파일을 찾을 수 없습니다. 경로를 확인해 주세요.")
        return

    # 마크다운 표 헤더 출력
    print("| Method | Size | Hit Rate@1 | Hit Rate@5 | MRR | nDCG@10 |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")
    
    for f in files:
        # 파일명에서 방식(Method)과 사이즈(Size) 추출
        filename = os.path.basename(f).replace("eval_", "").replace(".json", "")
        parts = filename.split("_")
        
        size = parts[-1]
        method = "_".join(parts[:-1])
        
        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)
            metrics = data.get("metrics", {})
            
            # 소수점 4자리까지 포매팅
            hr1 = metrics.get("hit_rate_at_1", 0)
            hr5 = metrics.get("hit_rate_at_k", 0)
            mrr = metrics.get("mrr", 0)
            ndcg = metrics.get("ndcg_at_k", 0)
            
            print(f"| {method} | {size} | {hr1:.4f} | {hr5:.4f} | {mrr:.4f} | {ndcg:.4f} |")

if __name__ == "__main__":
    main()