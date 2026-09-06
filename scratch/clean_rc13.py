with open(r"D:\kaggriculture\submission_rc13.py", "r", encoding="utf-8") as f:
    code = f.read()

debug_str = "    except Exception as e:\n        import traceback; traceback.print_exc()\n        return {\"farmer\": [\"PASS\"], \"hands\": [], \"market\": []}"
clean_str = "    except Exception as e:\n        return {\"farmer\": [\"PASS\"], \"hands\": [], \"market\": []}"

if debug_str in code:
    code = code.replace(debug_str, clean_str)

with open(r"D:\kaggriculture\submission_rc13.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Cleaned submission_rc13.py!")
