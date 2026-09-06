import json

with open(r"D:\kaggriculture\reports\ADVISOR_V02_PAIRED_AUDIT.json") as f:
    data = json.load(f)

print("Advisor v0.2 Summary Audit Analysis:")
print(f"RC2 Summary: {data['rc2_summary']}")
print(f"ADV Summary: {data['adv_summary']}")
print(f"Head to Head: {data['head_to_head']}")
