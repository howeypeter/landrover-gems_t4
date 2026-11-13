"""Build board2.kicad_pcb from board2.net + footprints (run with KiCad's python). Placement is rows; routing is NOT done."""
import pcbnew, re, os
from pcbnew import FromMM as mm, VECTOR2I
HERE=os.path.dirname(os.path.abspath(__file__))
FPDIR=r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
W,H=87.0,77.0
net=open(os.path.join(HERE,"board2.net"),encoding="utf-8").read()
fp_of={}
for m in re.finditer(r'\(comp\s+\(ref "([^"]+)"\)(.*?)\(footprint "([^"]+)"\)',net,re.S): fp_of[m.group(1)]=m.group(3)
nets={}
for m in re.finditer(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]+)"\)(.*?)(?=\(net\s+\(code|\Z)',net,re.S):
    nets[m.group(1).lstrip("/")]=re.findall(r'\(node\s+\(ref "([^"]+)"\)\s+\(pin "([^"]+)"\)',m.group(2))
b=pcbnew.BOARD()
ni={}
for n in nets:
    ni[n]=pcbnew.NETINFO_ITEM(b,n); b.Add(ni[n])
pinnet={(r,p):n for n,l in nets.items() for r,p in l}
# row layout: ref -> (center x, center y)  (board origin top-left)
# Signal flow bottom to top: J3 (bottom edge, plug opening facing the edge; pad numbers are mirrored in the footprint so
# pins read 1..16 left to right) -> J7 (J71 left, J72 right, wire entry up toward J6) -> J6 (rotated 180, entry faces J7)
# -> J4 grid at the top. Power chain right->left along y=42: J2 (right edge) -> D2 -> F2 -> D3(tap) -> SW1 (left edge);
# J6 above F2; SW2 below SW1.
# WORK IN PROGRESS (2026-11-12): F2, D2, D3 are parked off the board (to the right) while the power section is
# rearranged; their original spots were F2 (43.5,42), D2 (66,42), D3 (21,42). J71/J72 were moved up 2 mm.
pos={"J71":(W/2-15.9,53.0),"J72":(W/2+14.6,53.0),
     "J2":(W-6.2,42),"D2":(W+26.5,33.5),"F2":(W+26.5,18.5),"D3":(W+26.5,48.5),
     "SW1":(6.5,31),"SW2":(6.5,52.7),
     "J6":(45.0,30.2),"J3":(43.5,H-7)}   # J7/J6 x re-centred 2026-11-12 after the body-margin fix, so the pads stay where they were
ROT={"J2":90,"SW1":270,"SW2":270,"D3":180,"J3":180,"J71":180,"J72":180}   # edge terminals: wire entry faces the edge
# Synced from Cherry Blossom 2026-11-13 (CB x,y centred on the board, y up -> KiCad x+43.5, 38.5-y): these parts are placed
# by the position of their pad 1, not by the outline centre. J71/J72 turned 180 deg on the board (wire entry the other way),
# J6 back to 0 deg (it had been 180 deg only to compensate for the part's own orientation).
PAD1={"J3":(14.93,68.0),"J71":(40.6,55.3),"J72":(71.1,55.3),"J6":(32.0,28.9)}
# Power section synced from Cherry Blossom 2026-11-13: pad 1 and pad 2 target positions (KiCad mm). The footprints here are
# stand-ins whose pad layout differs slightly from Cherry Blossom's parts, so the rotation is chosen so that the pad 1 -> pad 2
# direction matches, and pad 1 is placed exactly. Right-edge column: J2, F2, D3 (x 81.3), D2 beside J2 (x 71.7); SW1/SW2 swapped.
PAD12={"J2":((81.3,17.54),(81.3,12.46)),"D2":((71.7,8.2),(71.7,21.8)),"F2":((81.3,26.5),(81.3,48.5)),
       "D3":((81.3,54.65),(81.3,67.15)),"SW1":((5.7,45.08),(5.7,50.16)),"SW2":((5.7,23.08),(5.7,28.16))}
for _r in PAD12: ROT.pop(_r,None)
for i in range(4):
    pos[f"J4{i+1}"]=(W/2-18+12*i,6.2); pos[f"J4{i+5}"]=(W/2-18+12*i,18.9)
for ref,fid in fp_of.items():
    lib,name=fid.split(":")
    f=pcbnew.FootprintLoad(os.path.join(HERE,"board2.pretty") if lib=="board2" else os.path.join(FPDIR,lib+".pretty"),name)
    f.SetReference(ref); f.SetValue(ref)
    for p in f.Pads():
        n=pinnet.get((ref,p.GetNumber()))
        if n: p.SetNet(ni[n])
    f.SetPosition(VECTOR2I(0,0))
    if ref in PAD12:
        (t1,t2)=PAD12[ref]; tv=(t2[0]-t1[0],t2[1]-t1[1]); best=None
        for ang in (0,90,180,270):
            f.SetOrientationDegrees(ang)
            pp={q.GetNumber():q.GetPosition() for q in f.Pads()}
            v=(pcbnew.ToMM(pp["2"].x-pp["1"].x),pcbnew.ToMM(pp["2"].y-pp["1"].y)); dot=v[0]*tv[0]+v[1]*tv[1]
            if best is None or dot>best[0]: best=(dot,ang)
        ROT[ref]=best[1]; PAD1[ref]=t1
    f.SetOrientationDegrees(ROT.get(ref,0)); c=f.GetBoundingBox(False,False).GetCenter()
    if ref in PAD1:
        p1=[q for q in f.Pads() if q.GetNumber()=="1"][0].GetPosition(); x,y=PAD1[ref]; f.Move(VECTOR2I(mm(x)-p1.x,mm(y)-p1.y))
    else:
        x,y=pos[ref]; f.Move(VECTOR2I(mm(x)-c.x,mm(y)-c.y))
    b.Add(f)
# outline
for (x1,y1,x2,y2) in [(0,0,W,0),(W,0,W,H),(W,H,0,H),(0,H,0,0)]:
    s=pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetStart(VECTOR2I(mm(x1),mm(y1))); s.SetEnd(VECTOR2I(mm(x2),mm(y2))); s.SetWidth(mm(0.1)); b.Add(s)
# mounting holes M3, 4 mm inset
for hx,hy in [(4.25,4.25),(W-4.25,4.25),(4.25,H-4.25),(W-4.25,H-4.25)]:
    f=pcbnew.FootprintLoad(os.path.join(FPDIR,"MountingHole.pretty"),"MountingHole_3.2mm_M3_Pad_Via")
    f.SetReference("H"); f.Reference().SetVisible(False); f.SetPosition(VECTOR2I(mm(hx),mm(hy))); b.Add(f)

# ---- silkscreen labels ----
def label(txt, x, y, size=0.9, rot=0, layer=pcbnew.F_SilkS):
    t=pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(layer)
    t.SetPosition(VECTOR2I(mm(x),mm(y))); t.SetTextSize(VECTOR2I(mm(size),mm(size))); t.SetTextThickness(mm(0.15))
    t.SetTextAngleDegrees(rot); b.Add(t)
fps={f.GetReference():f for f in b.GetFootprints()}
def pads_of(ref): return {p.GetNumber():(pcbnew.ToMM(p.GetPosition().x),pcbnew.ToMM(p.GetPosition().y)) for p in fps[ref].Pads()}
# J6: net names (labels sit outside the two pad rows)
p6=pads_of("J6"); m6=sum(y for x,y in p6.values())/len(p6)
for n,(x,y) in p6.items():
    i=int(n)-1; name=f"NET{i%4+1}{'ab'[i//4]}"
    label(name,x,y-1.6 if y<m6 else y+1.6,0.8)
# J7: OBD pin numbers, read from the net on each pad
def obdnum(ref,pad):
    nn=pinnet[(ref,pad)]
    return "5" if nn=="GND" else ("16" if nn=="V12S" else nn[3:])
for ref in ("J71","J72"):
    pp=pads_of(ref); mm_=sum(y for x,y in pp.values())/len(pp)
    for n,(x,y) in pp.items():
        label(obdnum(ref,n),x,y-1.6 if y<mm_ else y+1.6,0.9)
# J2 polarity: labels above/below the terminal (outside its body), nearest to each pad
p2=pads_of("J2"); cx=p2["1"][0]
# same places as the Cherry Blossom labels: GND above the terminal (clear of the corner mounting hole), +12V below it
label("GND", cx, 8.1, 0.9)
label("+12V", cx, 21.9, 0.9)
# designators of the power parts: references hidden, short labels placed in free spots
for _r in ("J2","D2","F2","D3"): fps[_r].Reference().SetVisible(False)
label("D2",71.7,5.4,0.9); label("F2 2A",73.0,37.5,0.9); label("D3",81.3,51.6,0.9)
# J4: reference + net, in the gap under each footprint (real refs hidden)
for r in range(2):
    for i in range(4):
        ref=f"J4{i+1+4*r}"; x,y=pads_of(ref)["1"]
        fps[ref].Reference().SetVisible(False)
        label(f"{ref} NET{i+1}{'ab'[r]}", x+1.5, y+(7.85 if r==0 else 7.1), 0.8)
# switch + title labels
for ref,txt in (("SW1","SW1 POWER"),("SW2","SW2 IGN")):
    fps[ref].Reference().SetVisible(False)
# SW2 (upper terminal): label above its first pad; SW1 (lower terminal): label below its last pad
sw2=pads_of("SW2"); sx,sy=sw2["1"]; label("SW2 IGN",sx,min(v[1] for v in sw2.values())-4.8,0.9)
sw1=pads_of("SW1"); sx,sy=sw1["1"]; label("SW1 POWER",sx,max(v[1] for v in sw1.values())+6.0,0.9)
# J3 pin labels (OBD pin number / function), above the pad row; ref hidden
fps["J3"].Reference().SetVisible(False)
for n,(x,y) in pads_of("J3").items():
    if int(n)==5: label("GND",x,y-3.6,0.8,90)   # pin 5: sideways "GND" replaces the number
    elif int(n)==16: label("+12V",x,y-4.0,0.8,90)   # pin 16: sideways "+12V" replaces the number
    else: label(str(int(n)),x,y-3.0,0.8)   # plain pin numbers 1..16 (J3 pads are numbered so they read 1..16 left to right)
# net legend
label("J4 PINS:",10.5,10.5,0.8); label("1=12V_BAT 2=NET",10.5,12.2,0.8); label("3=12V_IGN 4=GND",10.5,14,0.8)
label("Board 2 r1",10.5,16.5,0.8)
b.Save(os.path.join(HERE,"board2.kicad_pcb"))
print("saved")
