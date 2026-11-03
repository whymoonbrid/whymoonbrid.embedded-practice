# -*- coding: utf-8 -*-
"""
通过官方 pcbnew API 生成/重建 Simple_LDO_Board 的 board.kicad_pcb

用 D:\\KiCad\\bin\\python.exe 运行:
    "D:\\KiCad\\bin\\python.exe" kicad_api_gen.py

做的事:
  1. 备份旧的 board.kicad_pcb (如果是手搓的旧版)
  2. 新建 BOARD, 全程用 API 构建: 板框(Edge.Cuts) / 5个封装 / 走线(PCB_TRACK)
  3. SaveBoard 保存
  4. LoadBoard 回读校验: 封装数, 焊盘数, 走线数, 走线端点是否落在对应焊盘上
"""

import os
import shutil
import sys

import pcbnew

OUT_DIR = r"D:\whymoonbrid.embedded-practice\pcb\Simple_LDO_Board"
PCB_PATH = os.path.join(OUT_DIR, "board.kicad_pcb")

MM = pcbnew.FromMM


def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


# ------------------------------------------------------------------ 板框
BX0, BY0 = 100.0, 103.0
BW, BH = 20.0, 9.0
BX1, BY1 = BX0 + BW, BY0 + BH
CY = BY0 + BH / 2.0

J1_AT = (103.0, CY)
C1_AT = (107.0, CY)
U1_AT = (110.0, CY)
C2_AT = (113.0, CY)
J2_AT = (117.5, CY)


def draw_edge(board, p1, p2, width=0.05):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*p1))
    s.SetEnd(V(*p2))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(width))
    board.Add(s)


def draw_board_outline(board):
    draw_edge(board, (BX0, BY0), (BX1, BY0))
    draw_edge(board, (BX1, BY0), (BX1, BY1))
    draw_edge(board, (BX1, BY1), (BX0, BY1))
    draw_edge(board, (BX0, BY1), (BX0, BY0))


# ------------------------------------------------------------------ 网络
def get_net(board, name):
    try:
        n = board.FindNet(name)
        if n is not None:
            return n
    except Exception:
        pass
    n = pcbnew.NETINFO_ITEM(board, name)
    board.Add(n)
    return n


# ------------------------------------------------------------------ 封装
def make_fp(board, ref, value, at, ref_dy=-3.5, ref_size=0.6, val_size=0.5):
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("Simple_LDO", value))
    fp.SetPosition(V(*at))
    fp.SetReference(ref)
    fp.SetValue(value)
    board.Add(fp)
    # 位号: 丝印层, 小字号, 挪到元件上方
    f = fp.Reference()
    f.SetPosition(V(at[0], at[1] + ref_dy))
    f.SetLayer(pcbnew.F_SilkS)
    f.SetTextSize(pcbnew.VECTOR2I(MM(ref_size), MM(ref_size)))
    f.SetTextThickness(MM(ref_size * 0.16))
    # 值: 挪到 F.Fab 并隐藏, 不占丝印
    v = fp.Value()
    v.SetPosition(V(at[0], at[1] + abs(ref_dy)))
    v.SetLayer(pcbnew.F_Fab)
    v.SetTextSize(pcbnew.VECTOR2I(MM(val_size), MM(val_size)))
    v.SetTextThickness(MM(val_size * 0.16))
    try:
        v.SetVisible(False)
    except Exception:
        pass
    return fp


def add_pad(fp, number, x, y, w, h, net=None, kind="smd", shape=None, drill=None,
            roundrect_ratio=0.25):
    p = pcbnew.PAD(fp)
    p.SetNumber(str(number))

    if kind == "smd":
        p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.F_Cu)
        ls.AddLayer(pcbnew.F_Paste)
        ls.AddLayer(pcbnew.F_Mask)
        p.SetLayerSet(ls)
        sh = pcbnew.PAD_SHAPE_ROUNDRECT if shape is None else shape
        p.SetShape(sh)
        if sh == pcbnew.PAD_SHAPE_ROUNDRECT:
            try:
                p.SetRoundRectRadiusRatio(roundrect_ratio)
            except Exception:
                pass
    else:
        p.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
        ls = pcbnew.LSET.AllCuMask()
        ls.AddLayer(pcbnew.F_Mask)
        ls.AddLayer(pcbnew.B_Mask)
        p.SetLayerSet(ls)
        p.SetShape(pcbnew.PAD_SHAPE_CIRCLE if shape is None else shape)
        d = MM(1.0 if drill is None else drill)
        p.SetDrillSize(pcbnew.VECTOR2I(d, d))

    p.SetSize(pcbnew.VECTOR2I(MM(w), MM(h)))
    fp.Add(p)
    p.SetPosition(V(x, y))
    if net is not None:
        p.SetNet(net)
    return p


# ------------------------------------------------------------------ 走线
def add_track(board, p1, p2, net, width=0.4, layer=None):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(V(*p1))
    t.SetEnd(V(*p2))
    t.SetWidth(MM(width))
    t.SetLayer(pcbnew.F_Cu if layer is None else layer)
    t.SetNet(net)
    board.Add(t)
    return t


# ------------------------------------------------------------------ 过孔
def add_via(board, x, y, net, dia=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(x, y))
    v.SetWidth(MM(dia))
    try:
        v.SetDrill(MM(drill))
    except Exception:
        v.SetDrillSize(pcbnew.VECTOR2I(MM(drill), MM(drill)))
    try:
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    except Exception:
        pass
    v.SetNet(net)
    board.Add(v)
    return v


# ------------------------------------------------------------------ 建板
def build():
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)

    n_vbus = get_net(board, "VBUS")
    n_gnd = get_net(board, "GND")
    n_3v3 = get_net(board, "3V3")

    draw_board_outline(board)

    # ---- J1 Type-C (简化: 12 个 0.5mm pitch 信号焊盘, 贴左边居中)
    j1 = make_fp(board, "J1", "USB_C_Simplified", J1_AT, ref_dy=-3.9)
    tc_names = ["A1", "A2", "A3", "A4", "A5", "A6",
                "A7", "A8", "A9", "A10", "A11", "A12"]
    tc_net = {"A1": n_gnd, "A12": n_gnd, "A4": n_vbus, "A9": n_vbus}
    for i, nm in enumerate(tc_names):
        add_pad(j1, nm, J1_AT[0] - 1.4, J1_AT[1] - 2.75 + 0.5 * i,
                1.0, 0.3, tc_net.get(nm))

    # ---- C1 0805 10uF (输入)
    c1 = make_fp(board, "C1", "C_0805_10uF", C1_AT)
    add_pad(c1, "1", C1_AT[0] - 0.95, C1_AT[1], 1.0, 1.3, n_vbus)
    add_pad(c1, "2", C1_AT[0] + 0.95, C1_AT[1], 1.0, 1.3, n_gnd)

    # ---- U1 TLV75533 SOT-23-5: 1=IN 2=GND 3=EN 4=NC 5=OUT
    u1 = make_fp(board, "U1", "TLV75533_SOT-23-5", U1_AT, ref_dy=-4.0)
    # SOT-23-5: pitch 0.95 沿 y, 所以焊盘做成 长 x 宽 = 1.05 x 0.6
    add_pad(u1, "1", U1_AT[0] - 0.65, U1_AT[1] - 0.95, 1.05, 0.6, n_vbus)   # IN
    add_pad(u1, "2", U1_AT[0] - 0.65, U1_AT[1], 1.05, 0.6, n_gnd)           # GND
    add_pad(u1, "3", U1_AT[0] - 0.65, U1_AT[1] + 0.95, 1.05, 0.6, n_vbus)   # EN
    add_pad(u1, "4", U1_AT[0] + 0.65, U1_AT[1] + 0.475, 1.05, 0.6)          # NC
    add_pad(u1, "5", U1_AT[0] + 0.65, U1_AT[1] - 0.475, 1.05, 0.6, n_3v3)   # OUT

    # ---- C2 0805 10uF (输出)
    c2 = make_fp(board, "C2", "C_0805_10uF", C2_AT)
    add_pad(c2, "1", C2_AT[0] - 0.95, C2_AT[1], 1.0, 1.3, n_3v3)
    add_pad(c2, "2", C2_AT[0] + 0.95, C2_AT[1], 1.0, 1.3, n_gnd)

    # ---- J2 2Pin 排针 2.54
    j2 = make_fp(board, "J2", "PinHeader_1x02_2.54", J2_AT, ref_dy=-3.5)
    add_pad(j2, "1", J2_AT[0], J2_AT[1] - 1.27, 1.7, 1.7, n_3v3,
            kind="tht", shape=pcbnew.PAD_SHAPE_RECT, drill=1.0)
    add_pad(j2, "2", J2_AT[0], J2_AT[1] + 1.27, 1.7, 1.7, n_gnd,
            kind="tht", shape=pcbnew.PAD_SHAPE_CIRCLE, drill=1.0)

    # ---- 走线: VBUS  J1.A4 -> U1.IN
    # A4 处在 A3(105.9 下沿) 与 A5(106.6 上沿) 之间, 净空只有 0.2mm,
    # 所以出 J1 焊盘这段收紧到 0.2mm 线宽, 两侧各留 0.25mm;
    # 离开 J1 焊盘列(x>102.4)后马上加宽到 0.4mm
    add_track(board, (101.6, 106.25), (102.6, 106.25), n_vbus, width=0.2)   # 受限段
    add_track(board, (102.6, 106.25), (103.4, 106.30), n_vbus, width=0.3)   # 出焊盘列后抬高
    add_track(board, (103.4, 106.30), (109.35, 106.30), n_vbus, width=0.4)  # 主干
    add_track(board, (109.35, 106.30), (109.35, 106.55), n_vbus, width=0.4) # 进 U1.IN
    add_track(board, (106.05, 106.30), (106.05, 107.50), n_vbus, width=0.4) # 下到 C1.1
    # ---- 走线: 3V3   U1.OUT -> J2.1
    add_track(board, (110.65, 107.025), (110.65, 105.5), n_3v3)
    add_track(board, (110.65, 105.5), (117.5, 105.5), n_3v3)
    add_track(board, (117.5, 105.5), (117.5, 106.23), n_3v3)

    # ---- 走线: U1.EN -> VBUS, 从 GND 焊盘(2脚)下方绕
    # F.Cu 下探 -> 过孔 V1 -> B.Cu 从 pad2 底下横穿 -> 过孔 V2 -> F.Cu 接 VBUS 主干
    add_track(board, (109.35, 108.45), (109.35, 109.50), n_vbus, width=0.3)
    add_via(board, 109.35, 109.50, n_vbus)
    add_track(board, (109.35, 109.50), (107.60, 109.50), n_vbus, width=0.3,
              layer=pcbnew.B_Cu)
    add_track(board, (107.60, 109.50), (107.60, 105.90), n_vbus, width=0.3,
              layer=pcbnew.B_Cu)
    add_track(board, (107.60, 105.90), (108.00, 105.90), n_vbus, width=0.3,
              layer=pcbnew.B_Cu)
    add_via(board, 108.00, 105.90, n_vbus)
    add_track(board, (108.00, 105.90), (108.00, 106.30), n_vbus, width=0.3)

    return board


# ------------------------------------------------------------------ 校验
def verify(path):
    b = pcbnew.LoadBoard(path)
    fps = list(b.GetFootprints())
    pads = [p for fp in fps for p in fp.Pads()]
    allt = list(b.GetTracks())
    vias = [t for t in allt if t.Type() == pcbnew.PCB_VIA_T]
    tracks = [t for t in allt if t.Type() != pcbnew.PCB_VIA_T]
    print("[verify] footprints = %d" % len(fps))
    print("[verify] pads       = %d" % len(pads))
    print("[verify] tracks     = %d" % len(tracks))
    for v in vias:
        print("   via net=%-5s at (%.2f, %.2f) dia=%.2f drill=%.2f" % (
            v.GetNetname(), pcbnew.ToMM(v.GetPosition().x),
            pcbnew.ToMM(v.GetPosition().y), pcbnew.ToMM(v.GetWidth(pcbnew.F_Cu)),
            pcbnew.ToMM(v.GetDrill())))
    print("[verify] vias       = %d" % len(vias))
    for fp in fps:
        print("   %-3s %-24s pads=%2d  at (%.2f, %.2f)" % (
            fp.GetReference(), fp.GetValue(), len(list(fp.Pads())),
            pcbnew.ToMM(fp.GetPosition().x), pcbnew.ToMM(fp.GetPosition().y)))

    # 同一封装内焊盘重叠检查 (短路)
    for fp in fps:
        pl = list(fp.Pads())
        for i in range(len(pl)):
            for j in range(i + 1, len(pl)):
                if pl[i].GetBoundingBox().Intersects(pl[j].GetBoundingBox()):
                    print("   [COLLISION] %s pad %s / pad %s 重叠" % (
                        fp.GetReference(), pl[i].GetNumber(), pl[j].GetNumber()))
    # 走线与不同网络焊盘的间距
    def box(p):
        c, s = p.GetPosition(), p.GetSize()
        return (c.x - s.x / 2, c.x + s.x / 2, c.y - s.y / 2, c.y + s.y / 2)

    def gap(a, b):
        dx = max(a[0] - b[1], b[0] - a[1], 0)
        dy = max(a[2] - b[3], b[2] - a[3], 0)
        return (dx * dx + dy * dy) ** 0.5
    pad_ref = {}
    for fp in fps:
        for pad in fp.Pads():
            pad_ref[id(pad)] = fp.GetReference()
    for t in tracks + vias:
        isvia = t.Type() == pcbnew.PCB_VIA_T
        c1, c2 = t.GetStart(), t.GetEnd()
        w = t.GetWidth(pcbnew.F_Cu) if isvia else t.GetWidth()
        tb = (min(c1.x, c2.x) - w / 2, max(c1.x, c2.x) + w / 2,
              min(c1.y, c2.y) - w / 2, max(c1.y, c2.y) + w / 2)
        for pad in pads:
            if pad.GetNetname() == t.GetNetname():
                continue
            if not isvia and not pad.IsOnLayer(t.GetLayer()):
                continue
            g = pcbnew.ToMM(gap(tb, box(pad)))
            if g < 0.245:
                print("   [CLEARANCE] %s 与 %s.%s 间距 %.3fmm" % (
                    t.GetNetname(), (pad.GetParentFootprint().GetReference() if hasattr(pad, "GetParentFootprint") else "?"),
                    pad.GetNumber(), g))

    # 走线端点是否落在同网络焊盘上（折线拐点允许落在同网络的其它走线端点）
    ok = True
    for t in tracks:
        netname = t.GetNetname()
        for end in (t.GetStart(), t.GetEnd()):
            hit = [p for p in pads
                   if p.GetNetname() == netname
                   and p.HitTest(end)]
            if not hit:
                joint = [o for o in tracks
                         if o is not t and o.GetNetname() == netname
                         and (o.GetStart() == end or o.GetEnd() == end
                              or o.HitTest(end, 0))]
                if not joint:
                    ok = False
                    print("   [warn] track end (%0.2f,%0.2f) net=%s 没有压到焊盘" % (
                        pcbnew.ToMM(end.x), pcbnew.ToMM(end.y), netname))
    print("[verify] 端点贴合焊盘: %s" % ("PASS" if ok else "SEE WARNINGS"))
    return b


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(PCB_PATH):
        bak = PCB_PATH + ".bak"
        shutil.copy2(PCB_PATH, bak)
        print("[backup] %s" % bak)

    board = build()
    pcbnew.SaveBoard(PCB_PATH, board)
    print("[save] %s" % PCB_PATH)
    print("[size] %d bytes" % os.path.getsize(PCB_PATH))
    verify(PCB_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
