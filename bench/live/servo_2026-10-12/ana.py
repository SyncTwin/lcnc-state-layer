# SPDX-License-Identifier: GPL-2.0-or-later
import gzip, json, statistics as S, zlib, sys
def pct(a,p): a=sorted(a); return a[min(len(a)-1,int(round(p/100*(len(a)-1))))]
def merge(t,p):
    if not isinstance(p,dict): return p
    if not isinstance(t,dict): t={}
    for k,v in p.items():
        if v is None: t.pop(k,None)
        else: t[k]=merge(t.get(k),v)
    return t
D=lambda o: json.dumps(o,separators=(",",":"))
def deflate_model():
    c=zlib.compressobj(6,zlib.DEFLATED,-15)
    return lambda b: len(c.compress(b)+c.flush(zlib.Z_SYNC_FLUSH))-4
for name in ("rec_idle","rec_jog"):
    rows=[json.loads(l) for l in gzip.open(name+".jsonl.gz","rt")]
    pt=[];pb=[];fb=[];state=None;snap=None;defl_p=[];defl_f=[];dm=deflate_model();dmf=deflate_model()
    for r in rows:
        m=json.loads(r["raw"])
        if m["type"]=="snapshot": state=m["state"]; snap=len(r["raw"].encode()); continue
        if m["type"]!="patch": continue
        pt.append(r["t"]); b=r["raw"].encode(); pb.append(len(b)); defl_p.append(dm(b))
        state=merge(state,m["patch"]); f=D({"type":"patch","seq":m["seq"],"state":state}).encode(); fb.append(len(f)); defl_f.append(dmf(f))
    dt=[(b-a)*1000 for a,b in zip(pt,pt[1:])]
    print(f"== {name}: patches {len(pb)} snapshot {snap} B")
    print(f"  client dt ms: mean {S.mean(dt):.2f} sd {S.pstdev(dt):.2f} p50 {pct(dt,50):.2f} p99 {pct(dt,99):.2f} min {min(dt):.2f} max {max(dt):.2f}")
    print(f"  patch B mean {S.mean(pb):.0f} p95 {pct(pb,95)} | full B mean {S.mean(fb):.0f} | deflate patch mean {S.mean(defl_p):.0f} p95 {pct(defl_p,95)} | deflate full mean {S.mean(defl_f):.0f}")
# sidecar-side tick timing from trace
ts=[json.loads(l) for l in gzip.open("trace_live_100ms.jsonl.gz","rt")][1:]
t=[x["t"] for x in ts]; dt=[(b-a)*1000 for a,b in zip(t,t[1:])]
print(f"== trace ticks {len(t)}: dt ms mean {S.mean(dt):.2f} sd {S.pstdev(dt):.2f} p50 {pct(dt,50):.2f} p99 {pct(dt,99):.2f} max {max(dt):.2f}")
# changed fields share
from collections import Counter
c=Counter()
for a,b in zip(ts,ts[1:]):
    for k in b["stat"]:
        if a["stat"].get(k)!=b["stat"].get(k): c[k]+=1
n=len(ts)-1; print("  changed:", ", ".join(f"{k} {100*v/n:.0f}%" for k,v in c.most_common(12)))
# state transitions with time
prev=None
for x in ts:
    s=x["stat"]; key=(s["task_state"],s["task_mode"],s["estop"],s["enabled"])
    if key!=prev: print(f"  t={x['t']:.3f} task_state={s['task_state']} mode={s['task_mode']} estop={s['estop']} enabled={s['enabled']}"); prev=key
# samples: stream vs HAL
sm=json.load(open("rec_jog.summary.json"))
for s in sm["samples"]+json.load(open("rec_idle.summary.json"))["samples"][:2]:
    j=int(s["hal_enc_counts"])/1677721.6+709.594605
    print(f"  {s['tag']:9s} seq {s['seq']} hal_enc→mm {j:.4f} hal_fb {s['hal_motor_pos_fb']} stream {s['stream_joint0']:.4f} Δ {1000*(s['stream_joint0']-j):+.1f} µm")
print(json.load(open("rec_quick.summary.json"))["results"])
