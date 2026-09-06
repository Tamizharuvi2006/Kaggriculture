import os, glob, re, json

md_files = glob.glob("**/*.md", recursive=True)

catalog = []
for p in md_files:
    # Skip virtualenvs or build dirs if any
    if ".git" in p or "node_modules" in p: continue
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline().strip() for _ in range(30)]
        title = ""
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break
        if not title and lines:
            title = lines[0]
            
        full_text = " ".join(lines).lower()
        category = "other"
        if "phase" in p.lower(): category = "phase_market"
        elif "exp" in p.lower() or "experiment" in p.lower(): category = "experiments"
        elif "audit" in p.lower() or "governance" in p.lower() or "contract" in p.lower(): category = "audit_governance"
        elif "dissection" in p.lower() or "forensic" in p.lower() or "replay" in p.lower(): category = "replay_forensics"
        elif "apex" in p.lower() or "ppo" in p.lower() or "step" in p.lower(): category = "ml_apex"
        elif "market" in p.lower() or "price" in p.lower() or "economy" in p.lower(): category = "market_economy"
        
        catalog.append({
            "path": p.replace("\\", "/"),
            "title": title[:80],
            "category": category,
            "lines_count": sum(1 for _ in open(p, "r", encoding="utf-8", errors="ignore"))
        })
    except Exception as e:
        pass

by_cat = {}
for item in catalog:
    by_cat.setdefault(item["category"], []).append(item)

print(f"Total MD files indexed: {len(catalog)}")
for cat, items in sorted(by_cat.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"Category '{cat}': {len(items)} files")

with open("scratch/research_catalog.json", "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2)
print("Catalog saved to scratch/research_catalog.json")
