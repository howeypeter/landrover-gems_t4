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
R1,R2=14,31
pos={"J71":(21,R1),"J72":(53,R1),"J2":(79,R1),
     "J6":(21,R2),"SW1":(51,R2+2),"SW2":(76,R2+2),
     "D3":(79,45),"D2":(79,53.5),"F2":(76,62),"J3":(40,H-7)}
for i in range(4):
    pos[f"J4{i+1}"]=(14+12*i,46); pos[f"J4{i+5}"]=(14+12*i,57)
for ref,fid in fp_of.items():
    lib,name=fid.split(":")
    f=pcbnew.FootprintLoad(os.path.join(HERE,"board2.pretty") if lib=="board2" else os.path.join(FPDIR,lib+".pretty"),name)
    f.SetReference(ref); f.SetValue(ref)
    for p in f.Pads():
        n=pinnet.get((ref,p.GetNumber()))
        if n: p.SetNet(ni[n])
    f.SetPosition(VECTOR2I(0,0)); c=f.GetBoundingBox(False,False).GetCenter()
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
