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
# Signal flow bottom to top: J2 (bottom edge, plug opening facing the edge; pad numbers are mirrored in the footprint so
# pins read 1..16 left to right) -> J3/J4 (J3 left, J4 right, wire entry up toward J5) -> J5 (rotated 180, entry faces J7)
# -> J6-J9 grid at the top. Power chain right->left along y=42: J1 (right edge) -> D2 -> F2 -> D3(tap) -> SW1 (left edge);
# J5 above F2; SW2 below SW1.
# WORK IN PROGRESS (2026-11-12): F2, D2, D3 are parked off the board (to the right) while the power section is
# rearranged; their original spots were F2 (43.5,42), D2 (66,42), D3 (21,42). J3/J4 were moved up 2 mm.
pos={"J3":(W/2-15.9,53.0),"J4":(W/2+14.6,53.0),
     "J1":(W-6.2,42),"D2":(W+26.5,33.5),"F2":(W+26.5,18.5),"D3":(W+26.5,48.5),
     "SW1":(6.5,31),"SW2":(6.5,52.7),
     "J5":(45.0,30.2),"J2":(43.5,H-7)}   # J3/J4/J5 x re-centred 2026-11-12 after the body-margin fix, so the pads stay where they were
ROT={"J1":90,"SW1":270,"SW2":270,"D3":180,"J2":180,"J3":180,"J4":180}   # edge terminals: wire entry faces the edge
# Synced from Cherry Blossom 2026-11-13 (CB x,y centred on the board, y up -> KiCad x+43.5, 38.5-y): these parts are placed
# by the position of their pad 1, not by the outline centre. J3/J4 turned 180 deg on the board (wire entry the other way),
# J5 back to 0 deg (it had been 180 deg only to compensate for the part's own orientation).
PAD1={"J2":(14.93,68.0),"J3":(40.6,55.3),"J4":(71.1,55.3),"J5":(32.0,28.9)}
# Power section synced from Cherry Blossom 2026-11-13: pad 1 and pad 2 target positions (KiCad mm). The footprints here are
# stand-ins whose pad layout differs slightly from Cherry Blossom's parts, so the rotation is chosen so that the pad 1 -> pad 2
# direction matches, and pad 1 is placed exactly. Right-edge column: J1, F2, D3 (x 81.3), D2 beside J1 (x 71.7); SW1/SW2 swapped.
PAD12={"J1":((81.3,14.34),(81.3,11.8)),"D2":((70.2,21.8),(70.2,8.2)),"F2":((80.8,23.75),(80.8,38.75)),
       "D3":((81.3,52.75),(81.3,65.45)),"SW1":((5.7,37.08),(5.7,39.62)),"SW2":((5.7,15.08),(5.7,17.62))}   # SW1/SW2 moved up 8 mm (CB y +8) 2026-11-14
for _r in PAD12: ROT.pop(_r,None)
# J6-J9: four Harwin M20-9980546 2x5 headers side by side = one 5 row x 8 column grid (key row 4: pins pulled, no holes); cables exit up.
# Pad 1 / pad 2 targets from Cherry Blossom: columns 2.54 mm apart, row 1 at CB y = 33.08 (KiCad y 5.42); header i starts at CB x = -8.89 + 5.08 i.
for _i in range(4): PAD12[f"J{6+_i}"]=((43.5-8.89+5.08*_i,5.42),(43.5-8.89+5.08*_i+2.54,5.42))   # J6 at the -x end (left to right from the front); headers at 0 deg again (user 2026-11-14 flipped them 180 as parts): pins 1/2 at the J6-J9 edge   # back at 0 deg (2026-11-14, user: do not rotate the J6-J9 parts): pin 1/2 row nearest the J6-J9 edge
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
# mounting holes M4 (4.3 mm plated, 4.5 mm inset; matches Board 1 hole size)
for hx,hy in [(4.5,4.5),(W-4.5,4.5),(4.5,H-4.5),(W-4.5,H-4.5)]:
    f=pcbnew.FootprintLoad(os.path.join(FPDIR,"MountingHole.pretty"),"MountingHole_4.3mm_M4_Pad")
    for p in f.Pads(): p.SetSize(VECTOR2I(mm(8.0),mm(8.0)))   # 8.0 mm ring = 0.5 mm to the edge (same as CB)
    for g in list(f.GraphicalItems()):
        if g.GetLayer()==pcbnew.F_CrtYd: f.Remove(g)   # ring is the keep-out; stock courtyard is larger than the ring
    f.SetReference("H"); f.Reference().SetVisible(False); f.SetPosition(VECTOR2I(mm(hx),mm(hy))); b.Add(f)

# ---- silkscreen labels ----
def label(txt, x, y, size=0.9, rot=0, layer=pcbnew.F_SilkS, right=False, left=False):
    t=pcbnew.PCB_TEXT(b); t.SetText(txt); t.SetLayer(layer)
    if right: t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
    if left: t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    t.SetPosition(VECTOR2I(mm(x),mm(y))); t.SetTextSize(VECTOR2I(mm(size),mm(size))); t.SetTextThickness(mm(0.15))
    t.SetTextAngleDegrees(rot); b.Add(t)
fps={f.GetReference():f for f in b.GetFootprints()}
def pads_of(ref): return {p.GetNumber():(pcbnew.ToMM(p.GetPosition().x),pcbnew.ToMM(p.GetPosition().y)) for p in fps[ref].Pads()}
# J5: one net label per pin pair under the bottom row (as in Cherry Blossom 2026-11-14): pins 1,2 = NET1 ... pins 7,8 = NET4 (left to right).
# NOTE: the netlist still wires J5 pin 1/5 = NET1 etc.; the nets are to be reassigned later, so these labels lead the netlist.
for _t,_x in (("NET1",33.75),("NET2",40.75),("NET3",47.75),("NET4",54.75)): label(_t,_x,36.3,1.0)
for _t,_x in (("NET1",33.75),("NET2",40.75),("NET3",47.75),("NET4",54.75)): label(_t,_x,25.6,1.0)   # second set, above the J5 box (CB y 12.9)
# J3/J4: OBD pin numbers, read from the net on each pad
def obdnum(ref,pad):
    nn=pinnet[(ref,pad)]
    return "5" if nn=="GND" else ("16" if nn=="V12S" else nn[3:])
for ref in ("J3","J4"):
    pp=pads_of(ref); mm_=sum(y for x,y in pp.values())/len(pp)
    for n,(x,y) in pp.items():
        label(obdnum(ref,n),x,y-1.6 if y<mm_ else y+1.6,0.9)
for _r in ("J3","J4"): fps[_r].Reference().SetVisible(False)
label("J3",11.9,52.8,1.0); label("J4",76.1,52.8,1.0)   # designators on the short (outer) end of each block (CB -31.6/32.6, -14.3)
# J1 polarity: labels above/below the terminal (outside its body), nearest to each pad
p2=pads_of("J1"); cx=p2["1"][0]
# same places as the Cherry Blossom labels: GND above the terminal (clear of the corner mounting hole), +12V below it
label("GND", 75.9, 11.8, 1.0)   # left of J1 pad 2 = GND (CB 32.4, 26.7)
label("+12V", 75.5, 14.34, 1.0)   # left of J1 pad 1 = +12V (CB 32.0, 24.16)
# designators of the power parts: references hidden, short labels placed in free spots
for _r in ("J1","D2","F2","D3"): fps[_r].Reference().SetVisible(False)
label("D2",70.2,5.4,0.9); label("F2 2A",73.0,31.25,0.9); label("D3",85.6,60.95,1.0,90)   # right of D3 (CB 42.1,-22.45)
# J6-J9: labels as in Cherry Blossom (2026-11-14): headers turned 180 deg, text turned 180 deg so it reads from the J6-J9 edge.
# Centres from Cherry Blossom (x -> x+43.5, y -> 38.5-y). Real refs hidden; J6..J9 shown below the grid (toward J5). The key row (no holes) is unlabelled.
for _i in range(4): fps[f"J{6+_i}"].Reference().SetVisible(False)
for _t,_x,_y in (("+12V_SW",29.05,5.42),("+12V_IGN",28.5,7.96),("GND",31.05,10.5),("NET_SIGNAL",25.95,15.58)): label(_t,_x,_y,1.0)   # top to bottom (2026-11-14): BAT at the J6-J9 edge, key row blank, signal nearest J5
for _i in range(4): label(f"J{6+_i}",35.88+5.08*_i,2.3,1.0)
for _t,_x in (("NET1",35.88),("NET2",40.96),("NET3",46.04),("NET4",51.12)): label(_t,_x,19.5,1.0,90)   # on J8, J5 side, turned -90 deg (user 2026-11-14; nets to be reassigned later, so it does not match the J8 net yet)   # J6-J9 edge side of the grid (CB y 36.2), text at 0 deg (standard reading direction)
# J5 designator moved to the left side of its box (CB -17.3, 5.9)
fps["J5"].Reference().SetVisible(False); label("J5",26.2,32.6,1.0)
# switch terminals: names above each terminal (as in Cherry Blossom), pin names to the right of each pad, horizontal
for ref in ("SW1","SW2"): fps[ref].Reference().SetVisible(False)
sw2=pads_of("SW2"); sw1=pads_of("SW1")
label("SW2_IGN",5.5,38.5-26.6,1.0); label("SW1_BAT",5.5,38.5-5.0,1.0)
for _sw in (sw1,sw2):
    for _n,_nm in (("1","GND"),("2","LED+"),("3","OUT"),("4","IN")):
        _x,_y=_sw[_n]; label(_nm,10.3,_y,1.0,left=True)   # left-justified, left edge at CB x -33.2
# J2 pin labels (OBD pin number / function), centred halfway between the J2 end (KiCad y 66.8) and the J3/J4 bottom edge (57.6): y 62.2, as in Cherry Blossom; ref hidden
fps["J2"].Reference().SetVisible(False)
for n,(x,y) in pads_of("J2").items():
    if int(n)==5: label("SIG_GND",x,62.2,1.0,90)   # OBD pin 5 = signal ground (pin 4 chassis ground is not tied to GND); centred between J2 and J3/J4 (CB y -23.7)   # pin 5: sideways "GND" replaces the number
    elif int(n)==16: label("+12V",x,62.2,1.0,90)   # centred like SIG_GND (CB y -23.7)   # pin 16: sideways "+12V" replaces the number
    else: label(str(int(n)),x,62.2,0.8)   # plain pin numbers 1..16 (J2 pads are numbered so they read 1..16 left to right)
# net legend
REV="1.0"; REVDATE="2026-11"   # bump REV for every change to copper or silk sent to the fab
label("OBD2 BENCH BREAKOUT",34.0,41.0,1.0)   # title block, free area left of J5 (CB -13.5,-2.5)
label("J5 pairs tied:",19.5,26.7,1.0); label("2 wires per NET",19.5,28.2,1.0)   # tied-NET note, up-left of J5, between via rows (CB -22.2, 11.1 / 9.9)
label("Any OBD2 pin to any NET_SIGNAL output",34.0,42.8,1.0)
label(f"Board 2 - Rev {REV} - {REVDATE}",34.0,44.6,1.0)
b.Save(os.path.join(HERE,"board2.kicad_pcb"))
print("saved")
