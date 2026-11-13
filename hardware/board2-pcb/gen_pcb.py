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
ROT={"J2":90,"SW1":270,"SW2":270,"D3":180,"J3":180,"J6":180}   # edge terminals: wire entry faces the edge
for i in range(4):
    pos[f"J4{i+1}"]=(W/2-18+12*i,6.2); pos[f"J4{i+5}"]=(W/2-18+12*i,18.9)
for ref,fid in fp_of.items():
    lib,name=fid.split(":")
    f=pcbnew.FootprintLoad(os.path.join(HERE,"board2.pretty") if lib=="board2" else os.path.join(FPDIR,lib+".pretty"),name)
    f.SetReference(ref); f.SetValue(ref)
    for p in f.Pads():
        n=pinnet.get((ref,p.GetNumber()))
        if n: p.SetNet(ni[n])
    f.SetPosition(VECTOR2I(0,0)); f.SetOrientationDegrees(ROT.get(ref,0)); c=f.GetBoundingBox(False,False).GetCenter()
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
p2=pads_of("J2"); top=min(p2,key=lambda n:p2[n][1]); bot=max(p2,key=lambda n:p2[n][1])
cx=p2[top][0]
label("+12V" if top=="1" else "GND", cx, p2[top][1]-6.2, 0.9)
label("GND" if top=="1" else "+12V", cx, p2[bot][1]+6.2, 0.9)
# J4: reference + net, in the gap under each footprint (real refs hidden)
for r in range(2):
    for i in range(4):
        ref=f"J4{i+1+4*r}"; x,y=pads_of(ref)["1"]
        fps[ref].Reference().SetVisible(False)
        label(f"{ref} NET{i+1}{'ab'[r]}", x+1.5, y+(7.85 if r==0 else 7.1), 0.8)
# switch + title labels
for ref,txt in (("SW1","SW1 POWER"),("SW2","SW2 IGN")):
    fps[ref].Reference().SetVisible(False)
sx,sy=pads_of("SW1")["1"]; label("SW1 POWER",sx,18.6,0.9)
sx,sy=pads_of("SW2")["1"]; label("SW2 IGN",sx,66.3,0.9)
# J3 pin labels (OBD pin number / function), above the pad row; ref hidden
fps["J3"].Reference().SetVisible(False)
for n,(x,y) in pads_of("J3").items():
    if int(n)==5: label("GND",x,y-3.6,0.8,90)   # pin 5: sideways "GND" replaces the number
    elif int(n)==16: label("+12V",x,y-4.0,0.8,90)   # pin 16: sideways "+12V" replaces the number
    else: label(str(int(n)),x,y-3.0,0.8)   # plain pin numbers 1..16 (J3 pads are numbered so they read 1..16 left to right)
# net legend
label("J4 PINS:",10.5,10.5,0.8); label("1=12V_BAT 2=NET",10.5,12.2,0.8); label("3=12V_IGN 4=GND",10.5,14,0.8)
label("Board 2 r1",W-8,64.5,0.8)
b.Save(os.path.join(HERE,"board2.kicad_pcb"))
print("saved")
