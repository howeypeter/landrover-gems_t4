"""Build board2.kicad_pcb from board2.net + footprints (run with KiCad's python). Placement is rows; routing is NOT done."""
import pcbnew, re, os
from pcbnew import FromMM as mm, VECTOR2I
HERE=os.path.dirname(os.path.abspath(__file__))
FPDIR=r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
W,H=90.0,80.0
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
# power chain right->left along y=43: J2 (right edge) -> D2 -> F2 -> D3(tap) -> SW1 (left edge); J6 above F2; SW2 below SW1
pos={"J71":(W/2-15.5,59.5),"J72":(W/2+15.5,59.5),
     "J2":(84,43),"D2":(68,43),"F2":(46,43),"D3":(24,43),
     "SW1":(8.5,33),"SW2":(8.5,55),
     "J6":(46,30),"J3":(W/2,H-7)}
ROT={"J2":90,"SW1":270,"SW2":270,"D3":180}   # edge terminals: wire entry faces the edge
for i in range(4):
    pos[f"J4{i+1}"]=(W/2-18+12*i,6.2); pos[f"J4{i+5}"]=(W/2-18+12*i,17.4)
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
for hx,hy in [(4,4),(W-4,4),(4,H-4),(W-4,H-4)]:
    f=pcbnew.FootprintLoad(os.path.join(FPDIR,"MountingHole.pretty"),"MountingHole_3.2mm_M3_Pad_Via")
    f.SetReference("H"); f.Reference().SetVisible(False); f.SetPosition(VECTOR2I(mm(hx),mm(hy))); b.Add(f)
b.Save(os.path.join(HERE,"board2.kicad_pcb"))
print("saved")
