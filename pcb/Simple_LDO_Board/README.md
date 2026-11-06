# 极简 3.3V 稳压板（Simple_LDO_Board）

极简 LDO 稳压模块，把 USB Type-C 的 5V 降到 3.3V 给外部电路供电。

## 用途

为开发板 / 传感器等提供一路干净的 3.3V 电源。

## 核心器件

- LDO：`TLV75533`（SOT-23-5，3.3V 固定输出，低压差）
- 输入：1× Type-C 母座（5V）
- 输出：1× 2Pin 排针（3.3V / GND）
- 外围：输入、输出各 1 颗 10uF 0805 陶瓷电容

## 设计要点

- 所有元件沿一条直线排布，走线尽量短，追求极度简化。
- 一块两层板，已出 Gerber 并完成打样。
- 当前 DRC：0 违规 / 0 未连接项。

## 文件

- `board.kicad_pro` / `board.kicad_pcb` / `board.kicad_prl`：KiCad 工程
- `Simple_LDO.pretty/`：工程封装库，4 个封装（`TLV75533_SOT-23-5`、`C_0805_10uF`、`USB_C_Simplified`、`PinHeader_1x02_2.54`）
- `fp-lib-table`：封装库表，用 `${KIPRJMOD}` 指向 `Simple_LDO.pretty`，随工程走，不依赖全局配置
- `kicad_api_gen.py`：辅助生成脚本
- `brief.md`：需求速记

## 注意

- 本板已按早期版本打样，实物对应的是打样时的 Gerber。后续若改动源文件并重新制板，需重新导出 Gerber。
- 元件封装都定义在 `Simple_LDO.pretty/` 里，改动封装请同步更新该目录，否则 DRC 会报 `lib_footprint_issues`。
