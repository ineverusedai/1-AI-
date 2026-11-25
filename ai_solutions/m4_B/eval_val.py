import json, time, random, sys
from solver import solve
meta = json.load(open("val_data/dataset_metadata.json"))
rng = random.Random(12345); ok = 0; ts = []; wrong = []
for m in meta:
    opts = [m["target_option"]["text"]] + [d["text"] for d in m["distractors"]]
    rng.shuffle(opts)
    b = open(m["video_path"], "rb").read()
    t = time.time(); a = solve(b, opts); ts.append(time.time() - t)
    ok += a == m["text"]
    if a != m["text"]: wrong.append((m["id"], m["text"], a))
print(f"6-way acc {ok}/{len(meta)} = {ok/len(meta):.4f}; solve time mean {sum(ts)/len(ts):.3f}s max {max(ts):.3f}s")
print("wrong:", wrong)
